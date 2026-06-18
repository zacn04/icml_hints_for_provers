# Paper Revision Plan

Fill in the TBD values and finalize `leanpaper/main.tex` using experiment results in `outputs/`.

## Final Experiment Results

All experiments are complete. Here are the final numbers:

| Condition | k=16 | k=32 | k=64 |
|-----------|------|------|------|
| A-RL (i.i.d. baseline) | 38/244 (15.6%) | 42/244 (17.2%) | 42/244 (17.2%) |
| B-RL (skeleton schedule) | 55/244 (22.5%) | 58/244 (23.8%) | 60/244 (24.6%) |
| C1 (instruction paraphrases) | 38/244 (15.6%) | — | — |
| C2 (irrelevant comments) | 25/244 (10.2%) | — | — |
| A-BASE (i.i.d.) | 0/244 (0.0%) | 0/244 (0.0%) | 0/244 (0.0%) |
| B-BASE (skeletons) | 0/244 (0.0%) | 0/244 (0.0%) | 0/244 (0.0%) |

### Key findings:
- **Mode collapse confirmed**: A-RL flatlines k=32→k=64 (42→42)
- **Skeletons break plateau**: B-RL keeps climbing (55→58→60)
- **C1 paraphrases = baseline**: 38 = 38, diversity alone does nothing
- **C2 comments hurt**: 25 < 38, irrelevant tokens confuse the model
- **BASE model proves nothing**: 0/244 across all conditions — model just outputs `sorry`. RL is necessary for proof capability; skeletons can't substitute for it.

## Tasks

### 1. Fill in Table 2 (Diversity Ablation, line ~120-137)

Replace the TBD values in the ablation table:

- C2 (irrelevant comments): **25/244 (10.2%)**
- C1 (instruction paraphrases): **38/244 (15.6%)**
- Remove the footnote about "C1 and C2 experiments are completing" (line 137)
- Update caption to remove "preliminary" language
- Order the table: C2 < A-RL ≈ C1 < B-RL to tell a clear story

### 2. Fill in Table 3 (Base vs RL, line ~143-157)

Replace the "Running — results pending" with actual data:

- A-BASE: 0/244 (0.0%) at all k values
- B-BASE: 0/244 (0.0%) at all k values
- Update caption: the BASE model can't prove anything regardless of skeletons
- Reframe: this doesn't show "smaller gap from skeletons" as hypothesized — it shows BASE can't prove at all. The RL training is necessary for proof capability. The mode collapse story is RL-specific because only the RL model can prove in the first place.

### 3. Rewrite Section 4.3 (Base vs RL Discussion, line ~141-157)

The original hypothesis was "RL exacerbates mode collapse and BASE will show smaller skeleton gap." Reality is different: BASE proves 0 theorems. Reframe:

- BASE model outputs `sorry` for every theorem — it lacks proof capability entirely
- This means mode collapse is a phenomenon of RL-trained models specifically, because only RL models have proof capability to "collapse"
- Skeletons are a diagnostic/remedy for RL's mode collapse, not a general capability enhancer
- This is still interesting — it means RL creates the capability but simultaneously narrows it

### 4. Update abstract (line ~17)

- Remove "We further show that the non-RL base model benefits less from skeleton guidance" — it benefits zero because it can't prove anything
- Replace with something like: "We further show that the non-RL base model lacks proof capability entirely (0/244 across all conditions), confirming that mode collapse is a phenomenon specific to RL-trained models."

### 5. Update contribution bullet 3 (line ~34)

Change "RL training exacerbates mode collapse" framing. The BASE model proves nothing, so it's not about "smaller gap" — it's about RL being necessary for proof capability, with mode collapse as an RL side effect.

### 6. Fill in per-skeleton analysis (Section 4.4, line ~159-163)

Write a script to generate per-skeleton breakdown from the outputs:
```python
# Read all B-RL outputs, group by skeleton_id in attempt_results
# Count: theorems solved per skeleton, theorems UNIQUELY solved per skeleton
# Output: table of skeleton → solved count → unique count
```

The event files are in `outputs/*/events.jsonl`. Each event has fields like:
- `event`: "trial" or "run_start" or "run_end"
- `theorem_id`, `proved`, `attempt_results` (list with `skeleton_id`, `compiled`, etc.)
- `exp_key.baseline`, `exp_key.model`, `exp_key.k`, `exp_key.shard`

Note: `attempt_results` may be empty in some events. Check debug logs in `outputs/*/debug_logs/*/attempt_*.json` for per-attempt data including `tactic_prefix` (the skeleton used).

### 7. Compute Pass@15 (Section 4.5, line ~165-169)

From the attempt-level logs, compute pass@15 by excluding the 16th attempt (which in the original paper had a natural language hint). Compare pass@15 vs pass@16 for B-RL to show the hint's marginal contribution.

If attempt_results is empty in the events, parse the debug logs: each theorem dir has attempt_000.json through attempt_015.json with individual results.

### 8. Update Discussion section (line ~172+)

- Update "Mode collapse as the central finding" paragraph to incorporate BASE model result
- The C2 result (comments hurt performance) deserves a brief discussion — irrelevant tokens in the prompt actively degrade the model
- Mention that BASE model just outputs `sorry` — it hasn't learned to prove at all

### 9. Add missing citations to refs.bib

Add entries for:
- DSP (Draft, Sketch, Prove) — Jiang et al. 2023
- ConjectureBench — Li et al. 2025
- Lean 4 — de Moura et al. 2021
- Mathlib — mathlib community
- miniF2F — Zheng et al. 2022
- Goedel-Prover — Lin et al. 2025
- Kimina-Prover — Wang et al. 2025
- HyperTree — Lample et al. 2022
- COPRA — Thakur et al. 2023
- PACT — Han et al. 2022
- GPT-f — Polu & Sutskever 2020
- LeanDojo/ReProver — Yang et al. 2023
- AlphaProof — Trinh et al. 2024
- SEED (Chen et al. 2025) — if referenced
- Aristotle/Achim 2025 — if referenced

Check which cite keys are used in main.tex and ensure refs.bib has entries for all of them.

### 10. Format for target venue

If submitting to AI4Math @ ICML 2026 (deadline ~April 24, 2026):
- Check page limits and formatting requirements
- The current document uses plain `article` class — may need to switch to workshop template
- Add workshop-specific formatting if available

## Data locations

- Experiment outputs: `outputs/` (115 run directories)
- Each run: `outputs/<hash>/events.jsonl` + `outputs/<hash>/debug_logs/<theorem>/attempt_*.json`
- Paper: `leanpaper/main.tex`
- Bibliography: `leanpaper/refs.bib`
- Results aggregation script used on pod: was at `/tmp/results.py` (not saved locally — reconstruct from events.jsonl)
