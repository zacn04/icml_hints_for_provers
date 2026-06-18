# AutoForm: Experimental Results Summary

## Overview

**Project**: Structured Hints For Sample-Efficient Lean Theorem Proving
**Model**: DeepSeek-Prover-V1.5-RL
**Benchmark**: miniF2F (244 Lean 4 theorems)
**Hardware**: 8x NVIDIA H100 80GB HBM3

---

## Main Results

| Condition | Proved | Total | Pass Rate |
|-----------|--------|-------|-----------|
| Sample@16 | 37 | 244 | 15.2% |
| Structured@16 | 53 | 244 | 21.7% |
| **Improvement** | +16 | — | +6.5pp (43% relative) |

---

## Statistical Significance

### McNemar's Test (Paired Binary Outcomes)

| Category | Count |
|----------|-------|
| Proved by both methods | 34 |
| Only by structured | 19 |
| Only by sample | 3 |
| Neither | 188 |

**Test statistic**: χ² = 10.23 (with continuity correction)
**p-value**: 0.0014
**Result**: Highly significant (p < 0.01)

---

## Unique Contributions

### Theorems only solved by Structured Hints (19)

- amc12a_2002_p6
- amc12b_2002_p2
- amc12b_2002_p7
- mathd_algebra_114
- mathd_algebra_129
- mathd_algebra_141
- mathd_algebra_143
- mathd_algebra_208
- mathd_algebra_24
- mathd_algebra_302
- mathd_algebra_329
- mathd_algebra_388
- mathd_algebra_398
- mathd_algebra_400
- mathd_algebra_440
- mathd_algebra_441
- mathd_algebra_452
- mathd_numbertheory_341
- mathd_numbertheory_559

### Theorems only solved by Baseline Sampling (3)

- imo_1964_p2
- induction_11div10tonmn1ton
- mathd_algebra_419

---

## Experiment Details

### Structured@16
- **Experiment ID**: f56313e33f94
- **Configuration**: `baseline=structured`, `k=16`, `seed=1`
- **Method**: Tactic prefix injection + natural language hints

### Sample@16
- **Experiment ID**: 6034dd4befa9
- **Configuration**: `baseline=sample`, `k=16`, `seed=1`
- **Method**: Random sampling (temperature=0.6)

---

## Key Takeaways

1. **43% relative improvement** in pass@16 with structured hints
2. **Statistically significant** even with a single seed (p < 0.01)
3. **19 unique theorems** unlocked by structured hints vs only 3 lost
4. Structured hints particularly effective on algebra problems

---

## Suggested Paper Claim

> Structured hints improve pass@16 from 15.2% to 21.7% on miniF2F (+43% relative). McNemar's test confirms statistical significance (χ² = 10.23, p < 0.01), with structured hints uniquely solving 19 theorems compared to only 3 uniquely solved by baseline sampling.
