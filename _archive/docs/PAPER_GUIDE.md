# Paper Writing Guide

## Title (Fixed)

**Structured Hints For Sample-Efficient Lean Theorem Proving**

The title is fine—the key framing shift happens in the abstract and introduction, where you pose the research question and emphasize the *finding* over the *method*.

## Abstract (Draft)

State-of-the-art neural theorem provers like DeepSeek-Prover-V1.5 combine large language models with reinforcement learning, achieving impressive results through sophisticated training. **We ask: do these highly-trained models still benefit from simple structural guidance at inference time?** We evaluate two lightweight interventions—tactic prefix injection and natural language hints—on the miniF2F benchmark. Surprisingly, cycling through common tactic prefixes yields 21.7% pass@16 compared to 15.2% for standard sampling from the same model, a 43% relative improvement. Our results suggest that even capable RL-trained provers underutilize structural priors available in the tactic language, and that simple inference-time guidance remains a cheap, complementary boost—without requiring additional training.

---

## Section-by-Section Guide

### 1. Introduction (~1 page)

**Opening paragraph**: Set up the landscape
- Neural theorem proving has advanced rapidly
- SOTA systems (DeepSeek-Prover) use RL + MCTS, achieving ~60% on miniF2F
- These models are trained with sophisticated reward shaping and search

**Second paragraph**: Pose the research question
- With all this training, have these models fully internalized proof structure?
- Or do they still benefit from simple structural hints at inference time?
- This matters for understanding what RL training actually learns

**Third paragraph**: Your investigation
- We test two simple interventions: tactic prefix injection + natural language hints
- Evaluate on miniF2F with DeepSeek-Prover-V1.5-RL
- **Finding**: 43% relative improvement (15.2% → 21.7% pass@16)
- **Implication**: Even strong RL models underutilize tactic structure; simple guidance helps

**Framing tip**: Present this as an empirical investigation/analysis, not as proposing a novel method. The contribution is the *finding*, not the technique.

**Key citations for intro**:
- DeepSeek-Prover (2024), DeepSeek-Prover-V1.5 (2024)
- miniF2F benchmark paper
- Lean 4 / Mathlib

---

### 2. Related Work (~0.75 page)

**Neural theorem proving**:
- GPT-f, Minerva, early LLM provers
- DeepSeek-Prover series (RL + MCTS approach)
- AlphaProof (if you want to mention it)

**Proof search strategies**:
- MCTS for theorem proving
- Best-first search approaches
- Curriculum learning for provers

**Structured/guided generation**:
- Chain-of-thought prompting
- Constrained decoding
- Program synthesis with sketches (if applicable)

**Your positioning**: "We focus on inference-time structural guidance, complementary to training-time improvements like RL."

---

### 3. Method (~1-1.5 pages)

**3.1 Background**
- Brief Lean 4 / tactic proof background
- How DeepSeek-Prover-V1.5-RL works (at a high level)

**3.2 Structured Hints**

Your method has two components (from `ir.py`):

**Tactic Prefix Injection** (15 variants):
- Pre-fill the proof with common opening tactics
- Examples: `()`, `("simp",)`, `("intro",)`, `("constructor",)`, `("refine ?_",)`, `("simp", "try aesop")`
- The LLM then *continues* from this prefix

**Natural Language Goal Hints** (8 variants):
- Optional guidance text prepended to the prompt
- Examples:
  - `None` (no hint)
  - "Start by simplifying the goal and hypotheses using `simp`."
  - "If the goal is a conjunction or existence, build it using `constructor` or `refine`."
  - "If arithmetic is involved, try `norm_num`, then `linarith` or `nlinarith`."

**3.3 Search Procedure** (from `search.py`)
- `perturb()` generates k variants by cycling through (tactic_prefix, hint) combinations
- For k=16: mostly varies tactic prefixes (indices 0-15 mod 15), with hints cycling slower
- Each variant is tried until one proves the theorem or budget exhausted

**Baseline** (`run_sample_k`):
- Same base prompt (no prefix, no hint)
- Sample k times with different random seeds

**Figures to include**:
- Figure 1: Side-by-side comparison of sample vs structured prompts
- Figure 2: Example showing tactic prefix injection in action

---

### 4. Experiments (~1.5 pages)

**4.1 Setup**
- Benchmark: miniF2F (244 theorems, Lean 4 port)
- Model: DeepSeek-Prover-V1.5-RL (7B params)
- Hardware: 8x H100 GPUs on Azure ML
- Hyperparameters: temp=0.6, max_tokens=1024, k=16

**4.2 Baselines**
- `sample@16`: Standard sampling, take best of 16
- `structured@16`: Your method, 16 samples with hints

**4.3 Results**

| Method | pass@16 | Theorems Proved |
|--------|---------|-----------------|
| sample@16 | 15.2% | 37/244 |
| structured@16 | 21.7% | 53/244 |
| **Improvement** | **+6.5pp** | **+16 theorems** |

*Update with seed=2 results when available for error bars*

**4.4 Analysis** (optional but good)
- Which types of theorems benefit most?
- Failure case analysis
- Qualitative examples of successful structured proofs

---

### 5. Discussion & Limitations (~0.5 page)

**Limitations to acknowledge honestly**:
1. Single model (DeepSeek-Prover-V1.5-RL only)
2. Single benchmark (miniF2F only)
3. Hyperparameters differ from original paper (temp=0.6 vs 1.0, max_tokens=1024 vs 2048)
4. No comparison with full MCTS search
5. Limited compute budget (~$10k)

**Why results are still valid**:
- Controlled comparison (same model, same budget, same hyperparams for both conditions)
- The relative improvement is the key finding
- Suggests a direction worth exploring at scale

---

### 6. Conclusion (~0.25 page)

- Summarize: Structured hints improve sample efficiency by 43%
- Implication: Complements existing RL/MCTS approaches
- Future work: Combine with tree search, test on other benchmarks, scale up

---

## Results to Include

### Current Results (seed=1)
| Method | pass@16 |
|--------|---------|
| sample@16 [1024 tokens] | 37/244 = 15.2% |
| structured@16 [1024 tokens] | 53/244 = 21.7% |

### Pending (seed=2)
- Will provide error bars / confidence intervals
- Update abstract and results table when available

### Other data points (if you have them)
- sample@1: baseline single-shot performance
- Any k=1 structured results?

---

## Key Talking Points

1. **Research question, not novel method**: "Do RL-trained provers still benefit from simple structural guidance?"
2. **Surprising finding**: Yes—43% improvement from trivial interventions
3. **Controlled experiment**: Same model, same k, same hyperparams—only difference is tactic prefixes
4. **What this reveals**: RL training doesn't fully capture tactic structure priors
5. **Practical implication**: Cheap inference-time boost, no retraining needed
6. **Honest scope**: We're probing model behavior, not claiming a new architecture

---

## Anticipated Reviewer Questions

**Q: Why not compare to MCTS?**
A: Different compute regime. MCTS uses thousands of rollouts; we focus on fixed small budgets. Orthogonal techniques.

**Q: Why different hyperparameters than the original paper?**
A: Compute constraints. Key point is controlled comparison—both methods use identical settings.

**Q: Only one benchmark?**
A: miniF2F is the standard. Future work: ProofNet, LeanDojo, etc.

**Q: Why does this work?**
A: Hypothesis—structured hints reduce the search space by providing scaffolding. LLMs may be better at filling in details than inventing structure.

---

## Timeline Checklist

- [ ] Wait for seed=2 results
- [ ] Update results table with error bars
- [ ] Write Introduction
- [ ] Write Method section
- [ ] Write Related Work
- [ ] Write Experiments
- [ ] Write Discussion/Limitations
- [ ] Write Conclusion
- [ ] Create figures (overview diagram, example)
- [ ] Format for arXiv (use ICML template if targeting that)
- [ ] Proofread
- [ ] Submit to arXiv
- [ ] Submit to ICML 2026 (deadline: Jan 28, 2026)

---

## Useful References

```
@article{deepseek-prover,
  title={DeepSeek-Prover: Advancing Theorem Proving in LLMs through Large-Scale Synthetic Data},
  author={...},
  year={2024}
}

@article{deepseek-prover-v1.5,
  title={DeepSeek-Prover-V1.5: Harnessing Proof Assistant Feedback for Reinforcement Learning and Monte-Carlo Tree Search},
  author={...},
  year={2024}
}

@inproceedings{minif2f,
  title={miniF2F: a cross-system benchmark for formal Olympiad-level mathematics},
  author={Zheng et al.},
  year={2022}
}
```

---

## Notes

- Keep it concise—aim for 8 pages max (ICML format)
- Figures are important—one good diagram explains more than paragraphs
- Be honest about limitations upfront—reviewers respect that
- The 43% relative improvement is a strong result for a simple method
