"""
Search loop with Hybrid Prompting (Chat vs. Completion).
Automatically switches to 'Raw Completion' mode for DeepSeek-Prover.
"""
from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Optional

from .ir import make_base_ir, perturb, IR
from .model import Model
from .lean_runner import LeanResult, check

@dataclass(frozen=True)
class SearchOutcome:
    best: LeanResult
    attempts: int
    llm_calls: int
    proof_text: str | None


# ---------------------------------------------------------
# Prompt Strategies
# ---------------------------------------------------------

def _prompt_deepseek_completion(ir: IR) -> str:
    # Lean 4 / Mathlib4 header with explicit version marker
    header = "/- Lean 4 with Mathlib4 -/\nimport Mathlib\n\nopen BigOperators Real Nat Topology\n\n"
    hint_str = f"/-- Hint: {ir.goal_hint} -/\n" if ir.goal_hint else ""

    theorem = ir.theorem.rstrip()
    if theorem.endswith(":= by"):
        theorem = theorem[:-5].rstrip()

    if not ir.tactic_prefix:
        prompt_tail = ":= by\n"
    else:
        tactics_str = "\n  ".join(ir.tactic_prefix)
        prompt_tail = f":= by\n  {tactics_str}\n"   # <-- add newline

    return f"{header}{hint_str}{theorem}\n{prompt_tail}"



def _prompt_standard_chat(ir: IR) -> str:
    """
    Standard 'You are an expert' prompt for Chat models (GPT-4, Llama-3, Qwen).
    """
    prompt = """You are a Lean 4 theorem prover using Mathlib4.

Rules:
- Output ONLY Lean 4 tactic code (NOT Lean 3)
- Use Lean 4 naming: Real.log (not real.log), Nat.succ (not nat.succ)
- No explanations
- No markdown
- Do NOT repeat the theorem
- Do NOT include `by`
- If you cannot complete the proof, output `sorry`.

The theorem is:
"""
    prompt += ir.theorem + "\n\n"

    if ir.goal_hint:
        prompt += f"Hint: {ir.goal_hint}\n\n"

    prompt += "Complete the proof after `:= by`:\n"

    for tactic in ir.tactic_prefix:
        prompt += tactic + "\n"

    return prompt


def ir_to_prompt(ir: IR, model_name: str) -> str:
    """
    Dispatch based on model name.
    """
    if "DeepSeek-Prover" in model_name:
        return _prompt_deepseek_completion(ir)
    return _prompt_standard_chat(ir)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _clean_model_output(proof_body: str) -> str:
    proof_body = proof_body.strip()

    # Handle case where model hallucinates a full new prompt+proof
    # Extract proof from the LAST `:= by` block
    if ":= by" in proof_body:
        # Find last occurrence of := by
        last_by_idx = proof_body.rfind(":= by")
        if last_by_idx != -1:
            proof_body = proof_body[last_by_idx + 5:].strip()

    # Cut at ### (explanation/new prompt boundary) AFTER extracting
    if "###" in proof_body:
        proof_body = proof_body.split("###")[0].strip()

    # Remove markdown blocks
    if proof_body.startswith("```"):
        lines = proof_body.split("\n")
        # specific fix for '```lean' vs '```'
        proof_body = "\n".join(
            l for l in lines if not l.strip().startswith("```")
        ).strip()

    # Remove 'by' if the model added it redundantly
    if proof_body.startswith("by "):
        proof_body = proof_body[3:].strip()
    elif proof_body.startswith("by\n"):
        proof_body = proof_body[3:].strip()

    return proof_body


def _reconstruct_full_proof(ir: IR, raw_body: str, model_name: str) -> str:
    """
    Robustly reconstructs the valid Lean file from the fragments.
    Handles the case where the model completed a partial prefix.
    """
    clean_body = _clean_model_output(raw_body)
    
    # 1. Reassemble the tactic block
    # If the IR had a prefix, the model (especially DeepSeek) 
    # likely just continued after it. We must re-add the prefix.
    
    # Check if the body already contains the prefix (Chat models often repeat it).
    # This is a naive check; for production, you might want more robust overlapping.
    prefix_str = "\n".join(ir.tactic_prefix)
    
    if "DeepSeek-Prover" in model_name:
        # DeepSeek completion mode: The prompt ENDED with the prefix. 
        # The model output implies continuation.
        # We need to stitch them: prefix + clean_body
        final_tactics = f"{prefix_str}\n{clean_body}" if prefix_str else clean_body
    else:
        # Chat mode: We asked it to "Complete the proof".
        # Sometimes they repeat the prefix, sometimes they don't.
        # Safest bet for Chat: assume body is the WHOLE thing if it looks long,
        # otherwise prepend prefix. 
        # (For now, let's stick to your original simple logic for Chat, 
        # or enforce consistency).
        final_tactics = clean_body 
        # Note: If your Chat prompt says "Complete after prefix", you might need to
        # prepend prefix here too. But let's assume Chat output is full block for now.

    # 2. Construct valid Lean 4 syntax
    # We must ensure ':= by' exists. 
    # the body includes := by already...
    return f"{ir.theorem}\n{final_tactics}"


def _is_better(a: LeanResult, b: LeanResult) -> bool:
    if a.proved and not b.proved:
        return True
    if a.compiled and not b.compiled:
        return True
    if a.compiled == b.compiled and a.error_type == "unknown" and b.error_type != "unknown":
        return True
    return False


# ---------------------------------------------------------
# Search Loops
# ---------------------------------------------------------

def run_search(
    *,
    theorem: str,
    context: str,
    model: Model,
    seed: int,
    k_variants: int,
    timeout_sec: int,
    use_ir: bool = True,
    use_search: bool = True,
    use_feedback: bool = True,
    debug: bool = False,
    log_dir: Optional[Path] = None,
) -> SearchOutcome:
    if use_ir:
        base = make_base_ir(theorem, context)
    else:
        base = IR(theorem=theorem.strip(), tactic_prefix=(), goal_hint=None)
    
    variants = perturb(base, seed=seed, k=k_variants) if use_search else [base]

    best: LeanResult | None = None
    best_proof: str | None = None
    attempts = 0
    llm_calls = 0

    model_name = getattr(model, "name", "unknown")

    # Create log directory if specified
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)

    for attempt_idx, ir in enumerate(variants):
        # Dispatch prompt based on model type
        prompt = ir_to_prompt(ir, model_name)

        llm_calls += 1
        proof_body = model.generate(prompt=prompt, seed=seed)

        # Save prompt and output to file
        if log_dir:
            log_entry = {
                "attempt": attempt_idx,
                "theorem": ir.theorem,
                "tactic_prefix": list(ir.tactic_prefix),
                "goal_hint": ir.goal_hint,
                "prompt": prompt,
                "raw_output": proof_body,
                "seed": seed,
            }
            log_file = log_dir / f"attempt_{attempt_idx:03d}.json"
            with open(log_file, "w") as f:
                json.dump(log_entry, f, indent=2)

        if debug:
            print(f"\n[DEBUG] Prompt (Tail):\n...{prompt[-200:]}")
            print(f"[DEBUG] Output:\n{proof_body}\n")

        # Robust reconstruction
        full_proof = _reconstruct_full_proof(ir, proof_body, model_name)

        # Save reconstructed proof
        if log_dir:
            with open(log_dir / f"attempt_{attempt_idx:03d}_reconstructed.lean", "w") as f:
                f.write(full_proof)

        attempts += 1
        res = check(full_proof, timeout_sec=timeout_sec)

        # Log the result
        if log_dir:
            result_entry = {
                "attempt": attempt_idx,
                "proved": res.proved,
                "compiled": res.compiled,
                "error_type": res.error_type,
                "stderr_tail": res.stderr_tail,
                "time_ms": res.time_ms,
            }
            with open(log_dir / f"attempt_{attempt_idx:03d}_result.json", "w") as f:
                json.dump(result_entry, f, indent=2)

        if best is None or _is_better(res, best):
            best = res
            best_proof = full_proof

        if res.proved:
            break

        if not use_feedback:
            break

    return SearchOutcome(best=best, attempts=attempts, llm_calls=llm_calls, proof_text=best_proof)


def run_oneshot(
    *,
    theorem: str,
    context: str,
    model: Model,
    seed: int,
    timeout_sec: int,
    log_dir: Optional[Path] = None,
) -> SearchOutcome:
    base = make_base_ir(theorem, context)
    model_name = getattr(model, "name", "unknown")
    
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
    
    prompt = ir_to_prompt(base, model_name)
    proof_body = model.generate(prompt=prompt, seed=seed)
    
    # Save prompt and output
    if log_dir:
        log_entry = {
            "attempt": 0,
            "theorem": base.theorem,
            "tactic_prefix": list(base.tactic_prefix),
            "goal_hint": base.goal_hint,
            "prompt": prompt,
            "raw_output": proof_body,
            "seed": seed,
        }
        with open(log_dir / "attempt_000.json", "w") as f:
            json.dump(log_entry, f, indent=2)
    
    full_proof = _reconstruct_full_proof(base, proof_body, model_name)
    
    if log_dir:
        with open(log_dir / "attempt_000_reconstructed.lean", "w") as f:
            f.write(full_proof)
    
    res = check(full_proof, timeout_sec=timeout_sec)
    
    if log_dir:
        result_entry = {
            "attempt": 0,
            "proved": res.proved,
            "compiled": res.compiled,
            "error_type": res.error_type,
            "stderr_tail": res.stderr_tail,
            "time_ms": res.time_ms,
        }
        with open(log_dir / "attempt_000_result.json", "w") as f:
            json.dump(result_entry, f, indent=2)

    return SearchOutcome(
        best=res,
        attempts=1,
        llm_calls=1,
        proof_text=full_proof if res.proved else None,
    )


def run_sample_k(
    *,
    theorem: str,
    context: str,
    model: Model,
    seed: int,
    k: int,
    timeout_sec: int,
    log_dir: Optional[Path] = None,
) -> SearchOutcome:
    base = make_base_ir(theorem, context)
    model_name = getattr(model, "name", "unknown")

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)

    best: LeanResult | None = None
    best_proof = None
    attempts = 0
    llm_calls = 0

    for i in range(k):
        prompt = ir_to_prompt(base, model_name)
        llm_calls += 1
        proof_body = model.generate(prompt=prompt, seed=seed + i)
        
        # Save prompt and output
        if log_dir:
            log_entry = {
                "attempt": i,
                "theorem": base.theorem,
                "tactic_prefix": list(base.tactic_prefix),
                "goal_hint": base.goal_hint,
                "prompt": prompt,
                "raw_output": proof_body,
                "seed": seed + i,
            }
            with open(log_dir / f"attempt_{i:03d}.json", "w") as f:
                json.dump(log_entry, f, indent=2)
        
        full_proof = _reconstruct_full_proof(base, proof_body, model_name)
        
        if log_dir:
            with open(log_dir / f"attempt_{i:03d}_reconstructed.lean", "w") as f:
                f.write(full_proof)
        
        attempts += 1
        res = check(full_proof, timeout_sec=timeout_sec)
        
        if log_dir:
            result_entry = {
                "attempt": i,
                "proved": res.proved,
                "compiled": res.compiled,
                "error_type": res.error_type,
                "stderr_tail": res.stderr_tail,
                "time_ms": res.time_ms,
            }
            with open(log_dir / f"attempt_{i:03d}_result.json", "w") as f:
                json.dump(result_entry, f, indent=2)

        if best is None or _is_better(res, best):
            best = res
            best_proof = full_proof

        if res.proved:
            break

    return SearchOutcome(best=best, attempts=attempts, llm_calls=llm_calls, proof_text=best_proof)