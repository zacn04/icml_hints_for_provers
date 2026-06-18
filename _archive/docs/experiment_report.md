# Structured Hints Revision — Experiment Report

**Date**: 2026-03-28
**Author**: Zac Burton
**Status**: Running on Prime Intellect (1x A100 80GB PCIe, massedcompute US)

---

## Motivation

The original ICML 2026 submission ("Structured Hints for Sample-Efficient Lean Theorem Proving", #6719) received four reject reviews (scores: 2, 2, 2, 1). All reviewers agreed the core finding was interesting but the evaluation was too narrow. This experiment suite directly addresses every major criticism.

### Reviewer Criticisms Addressed

| Criticism | Reviewer(s) | Experiment |
|-----------|-------------|------------|
| Limited to k=16, no scaling analysis | yvsa, H7Ko | Exp 1: pass@16, 32, 64 |
| Only one model (RL-specific?) | yvsa, H7Ko, WyAw | Exp 2: BASE vs RL comparison |
| Prompt diversity confound — gains from diverse prompts, not skeletons? | H7Ko, e4mq | Exp 3: C1 (paraphrase), C2 (comment) ablations |
| Missing per-skeleton analysis | H7Ko, WyAw | Exp 4a: from per-attempt logs (free) |
| Attempt 16 NL hint confound | H7Ko, PAT | Exp 4c: pass@15 from per-attempt logs (free) |
| Lean version mismatch (v4.27 vs v4.9 model was trained on) | e4mq | Pinned to Lean v4.9.0-rc1 + mathlib `7fa489a5` |
| Missing citations (DSP, ConjectureBench, tree-based provers, Lean 4) | WyAw, e4mq | Paper revision (separate) |

### Criticism NOT Addressed (acknowledged in limitations)
- Other benchmarks (ProofNet, FIMO, PutnamBench) — would require new benchmark infrastructure
- Other models (Goedel-Prover, Kimina-Prover, GPT-4) — cost-prohibitive or API-only
- Constrained decoding / multi-turn setups — future work

---

## Experimental Setup

### Models
- **DeepSeek-Prover-V1.5-RL** (`deepseek-ai/DeepSeek-Prover-V1.5-RL`): 7B params, RL-trained on Lean proofs
- **DeepSeek-Prover-V1.5-BASE** (`deepseek-ai/DeepSeek-Prover-V1.5`): Same architecture, no RL

### Benchmark
- **miniF2F-test**: 244 theorems (same split as original paper)

### Lean Environment
- **Lean**: v4.9.0-rc1 (matches DS-Prover-V1.5 training environment)
- **Mathlib**: commit `7fa489a5cbf3c4f08d36e1e0b5dee4d761fdbd9b` (last v4.9.0-rc1-compatible)
- This directly addresses Reviewer e4mq's strongest criticism about newer Lean tactics being more powerful.

### Decoding Config (held constant across ALL conditions)
- Temperature: 0.6
- Max tokens: 1024
- top_p: 0.95
- Completion mode (not chat) — raw Lean prefix completion

### Infrastructure
- **Inference**: vLLM v0.18 on Prime Intellect A100 80GB PCIe
- **Verification**: `lake env lean --json` against pinned Lean/Mathlib
- **Parallelism**: 8-way sharding per condition (8 parallel Lean verification processes)
- **Logging**: Per-attempt JSONL with skeleton_id, condition, proved/compiled/error_type

---

## Experiment Conditions

### Experiment 1: Extended Budget (kills "limited to k=16")

| Condition | Model | Prompt Strategy | k values |
|-----------|-------|-----------------|----------|
| A-RL | DS-Prover-V1.5-RL | Standard (i.i.d. sampling, no skeleton) | 16, 32, 64 |
| B-RL | DS-Prover-V1.5-RL | 15-skeleton schedule, cycling | 16, 32, 64 |

**Key question**: Does the gap persist, shrink, or grow with more samples?

### Experiment 2: Base vs RL (kills "only one model" + "is this RL-specific?")

| Condition | Model | Prompt Strategy | k values |
|-----------|-------|-----------------|----------|
| A-BASE | DS-Prover-V1.5-BASE | Standard (i.i.d. sampling) | 16, 32, 64 |
| B-BASE | DS-Prover-V1.5-BASE | 15-skeleton schedule, cycling | 16, 32, 64 |

**Key question**: Do non-RL models also benefit? If gap is smaller for BASE, supports the mode-collapse-from-RL narrative.

### Experiment 3: Diversity Ablation (kills the main confound)

| Condition | Model | Prompt Strategy | k |
|-----------|-------|-----------------|---|
| C1 | DS-Prover-V1.5-RL | 16 instruction paraphrases (no tactic skeletons) | 16 |
| C2 | DS-Prover-V1.5-RL | 16 irrelevant Lean comments (pure token perturbation) | 16 |

**Key question**: Is the improvement from structural guidance, semantic diversity, or any prompt perturbation?

**Outcome matrix**:
- B-RL >> C1 ≈ C2 ≈ A-RL → structural guidance does real work (best outcome)
- C1 ≈ B-RL >> A-RL → any semantic diversity helps, not skeleton-specific
- C1 ≈ C2 ≈ B-RL >> A-RL → any prompt perturbation breaks mode collapse
- B-RL > C1 > C2 ≈ A-RL → gradient from random → semantic → structural (most interesting)

### Experiment 4: Analysis (free from existing data)

**4a. Per-skeleton breakdown**: From per-attempt logs, tabulate which skeletons solve what, and how many theorems each uniquely solves.

**4c. Pass@15 reporting**: Exclude attempt 16 (which had the NL hint confound) and report pass@15 alongside pass@16 for all conditions.

---

## Perturbation Modes

### Skeleton Mode (conditions A/B)
Cycles through 15 tactic prefixes:
`()`, `(simp,)`, `(intro,)`, `(intros,)`, `(constructor,)`, `(refine ?_,)`, `(refine ⟨?_, ?_⟩,)`, `(aesop,)`, `(norm_num,)`, `(linarith,)`, `(nlinarith,)`, `(ring,)`, `(ring_nf,)`, `(simp, try aesop)`, `(simp, try nlinarith)`

### Paraphrase Mode (condition C1)
Cycles through 16 instruction variants as Lean comments:
"Prove the following theorem in Lean 4:", "Complete this Lean 4 proof:", ..., "Prove the following:"

### Comment Mode (condition C2)
Cycles through 16 semantically irrelevant Lean comments:
`/- approach alpha -/`, `/- strategy beta -/`, ..., `/- take pi -/`

---

## Compute Budget

| Phase | Conditions | Est. time (8 shards) | Cost @ $1.20/hr |
|-------|-----------|---------------------|-----------------|
| Exp 1+3 (RL model) | 8 conditions | ~8.5 hr | ~$10 |
| Exp 2 (BASE model) | 6 conditions | ~4 hr | ~$5 |
| **Total** | **14 conditions** | **~12.5 hr** | **~$15** |

---

## Output Format

Each condition produces `outputs/<exp_hash>/events.jsonl` with per-theorem trials:

```json
{
  "event": "trial",
  "theorem_id": "mathd_algebra_478",
  "model": "deepseek-ai/DeepSeek-Prover-V1.5-RL",
  "baseline": "structured",
  "perturbation_mode": "skeleton",
  "condition": "B-RL",
  "k": 16,
  "proved": true,
  "compiled": true,
  "lean_attempts": 5,
  "llm_calls": 5,
  "time_ms": 3200,
  "trial_time_ms": 45000,
  "error_type": "ok",
  "attempt_results": [
    {"attempt_idx": 0, "skeleton_id": 0, "proved": false, "compiled": false, "error_type": "unsolved_goals"},
    {"attempt_idx": 1, "skeleton_id": 1, "proved": false, "compiled": true, "error_type": "unsolved_goals"},
    {"attempt_idx": 4, "skeleton_id": 4, "proved": true, "compiled": true, "error_type": "ok"}
  ]
}
```

The `attempt_results` field enables:
- **Per-skeleton analysis** (Exp 4a): aggregate by `skeleton_id`
- **Pass@15 reporting** (Exp 4c): filter to `attempt_idx < 15`
- **Failure mode analysis**: error_type distributions per condition

---

## Post-Experiment Analysis Plan

Once data is collected:

1. **Main results table**: Pass@k for all conditions at k=16, 32, 64
2. **Scaling curve**: Plot pass@k vs k for A-RL vs B-RL (does gap grow/shrink?)
3. **Diversity ablation table**: A-RL vs B-RL vs C1 vs C2 at k=16
4. **Base vs RL comparison**: Does BASE benefit more or less?
5. **Per-skeleton breakdown**: Table of per-skeleton solve rates + unique contributions
6. **Pass@15 vs pass@16**: Isolate NL hint effect
7. **McNemar's test**: Paired significance for each comparison
8. **Error distribution**: Failure modes per condition

---

## Reproducibility

All code is at `github.com/zacn04/autoform` (private).

To reproduce:
```bash
# 1. Rent A100 80GB
# 2. Clone repo, run setup
git clone https://github.com/zacn04/autoform.git
cd autoform
bash scripts/setup_prime_pod.sh

# 3. Run full pipeline
export HF_TOKEN=<your-token>
bash scripts/run_full_pipeline.sh
```

Exact versions:
- vLLM: 0.18.0
- Lean: 4.9.0-rc1
- Mathlib: `7fa489a5cbf3c4f08d36e1e0b5dee4d761fdbd9b`
- DeepSeek-Prover-V1.5-RL: `deepseek-ai/DeepSeek-Prover-V1.5-RL` (HuggingFace)
- DeepSeek-Prover-V1.5-BASE: `deepseek-ai/DeepSeek-Prover-V1.5` (HuggingFace)
