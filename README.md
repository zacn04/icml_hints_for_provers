# autoform

Code, prompts, and per-attempt logs for the ICML AI4Math 2026 workshop paper:

> **Inference-Time Diversity in RL-Trained Lean Theorem Provers: A Diagnostic Study**
> Zachary Burton.
> [arXiv:2601.16172](https://arxiv.org/abs/2601.16172)

RL-trained Lean theorem provers mode-collapse at inference time. On miniF2F-test with
DeepSeek-Prover-V1.5-RL, doubling the i.i.d. sampling budget from k=32 to k=64
produces zero additional solved theorems (42/244 in both). A fixed schedule of 15
tactic skeletons breaks the plateau (mean Δ = +12.3 ± 4.2 theorems across n=3 seeds).
A controlled diversity ablation isolates the mechanism: tactic skeletons help,
instruction paraphrases match the topline, irrelevant Lean comments degrade.
The phenomenon is RL-specific: V1.5-Base proves zero theorems with or without
skeletons. Full results in the [paper](https://arxiv.org/abs/2601.16172).

## Setup

```bash
# 1. Python environment
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Lean toolchain (pinned to v4.9.0-rc1 — matches DeepSeek-Prover-V1.5)
curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh -s -- -y
export PATH="$HOME/.elan/bin:$PATH"
(cd lean && lake update && lake exe cache get && lake build)

# 3. (Optional) Start a local vLLM server for an open-source prover
python -m vllm.entrypoints.openai.api_server \
  --model deepseek-ai/DeepSeek-Prover-V1.5-RL \
  --tensor-parallel-size 1 --max-model-len 2048 --gpu-memory-utilization 0.9 \
  --enforce-eager --trust-remote-code
```

The provided pod-bootstrap script (`scripts/setup_prime_pod.sh`) handles all three
steps end-to-end on a fresh Prime Intellect / RunPod A100 instance.

## Reproduce the main results

Each experiment writes append-only `events.jsonl` and per-attempt JSON / Lean files
under `outputs/<exp_hash>/`. Hashes are deterministic functions of the run config,
so reruns are idempotent.

```bash
# Experiment 1 + Experiment 3 (RL model: V1.5-RL): A-RL, B-RL at k ∈ {16, 32, 64},
# plus the C1 (paraphrase) and C2 (comment) diversity ablations at k=16.
bash scripts/run_exp1_exp3_rl.sh --provider openai_compat

# Experiment 2 (Base model: V1.5): A-BASE, B-BASE at k ∈ {16, 32, 64}.
bash scripts/run_exp2_base.sh --provider openai_compat

# Cross-model extension (V2-7B, Kimina-Prover-Preview-Distill-7B):
# A and B at k ∈ {16, 32}, max-tokens 8192 for reasoning-mode CoT.
bash scripts/run_new_models.sh
```

For an 8-way-sharded version of any single condition:

```bash
bash scripts/run_sharded.sh \
  --model deepseek-ai/DeepSeek-Prover-V1.5-RL \
  --baseline structured --perturbation skeleton --k 16 \
  --condition B-RL --shards 8 --provider openai_compat
```

To run one condition directly (no sharding wrapper):

```bash
python3 run.py \
  --benchmark benchmarks/minif2f.jsonl \
  --model deepseek-ai/DeepSeek-Prover-V1.5-RL \
  --baseline structured --perturbation skeleton \
  --k 16 --timeout 120 --seed 1 \
  --provider openai_compat --condition B-RL \
  --output-root outputs
```

## Analysis

The analysis scripts read `outputs/<hash>/events.jsonl` + `outputs/<hash>/debug_logs/`
and accept an `--outputs DIR` flag (also via `AUTOFORM_OUTPUTS=<dir>`).

```bash
python3 scripts/analyze_significance.py            # paired-bootstrap CIs over A vs B
python3 scripts/per_skeleton_analysis.py           # per-skeleton solved / unique counts
python3 scripts/empty_analysis.py                  # pass@k for the empty skeleton (k=1 baseline)
python3 scripts/venn_sorry_analysis.py             # Venn(A-RL, B-RL) + sorry-rate breakdown
python3 figures/venn_diagram.py                    # writes figures/venn_overlap.{pdf,png}
```

## Repo structure

```
run.py                      # Entry point: one experiment run → outputs/<hash>/events.jsonl
autoform/                   # Python package
  ir.py                     # IR + skeleton/paraphrase/comment perturbations
  model.py                  # Model backends: HF, Ollama, OpenAI-compatible (vLLM)
  search.py                 # Search loop + per-prover prompt strategies
  lean_runner.py            # lake env lean --json verification harness
lean/                       # Lean 4 + Mathlib project (pinned at v4.9.0-rc1)
benchmarks/
  minif2f.jsonl             # miniF2F-test (244 theorems, Lean 4 / Mathlib)
  minif2f_easy.jsonl        # Easy subset for smoke tests
  port_minif2f.py           # Port script (miniF2F-lean3 → miniF2F-lean4)
scripts/
  setup_prime_pod.sh        # Bootstrap a fresh A100 pod (vLLM + elan + Mathlib + weights)
  run_full_pipeline.sh      # End-to-end: V1.5-RL → V1.5-BASE switch, all conditions
  run_exp1_exp3_rl.sh       # A-RL, B-RL, C1, C2 on V1.5-RL
  run_exp2_base.sh          # A-BASE, B-BASE on V1.5-BASE
  run_new_models.sh         # V2-7B + Kimina (chat / reasoning mode)
  run_sharded.sh            # 8-way sharding wrapper for a single condition
  *_analysis.py             # See "Analysis" above
configs/ir_search.yaml      # Reference YAML config (paths + decoding params)
env/                        # Conda environment specs (alternative to requirements.txt)
figures/                    # Venn-diagram plotting source
leanpaper/                  # Paper source (main.tex + refs.bib + ICML submission)
Dockerfile, .dockerignore   # Reproducible image with elan + Mathlib cache
```

## Output schema

`outputs/<exp_hash>/events.jsonl` is append-only:

| event           | fields |
|-----------------|--------|
| `run_start`     | `exp_id`, `exp_key`, `git`, `gpus`, `argv` |
| `trial`         | `theorem_id`, `proved`, `compiled`, `lean_attempts`, `attempt_results` |
| `trial_error`   | `theorem_id`, `error` |
| `run_end`       | `exp_id` |

`exp_key` is a sorted-dict signature of (benchmark, model, baseline, perturbation,
k, timeout, seed, shard, num_shards). Its 12-char SHA-256 prefix is the directory
name, which makes reruns of an identical configuration write to the same place.

Per-attempt detail (prompt, raw model output, sanitized proof, Lean stderr) lives
in `outputs/<exp_hash>/debug_logs/<theorem_id>/attempt_NNN{,_result,_reconstructed}.{json,lean}`.

## Models evaluated

| Model | Mode | max-tokens | Source |
|-------|------|-----------|--------|
| DeepSeek-Prover-V1.5-RL  | completion | 1024 | `deepseek-ai/DeepSeek-Prover-V1.5-RL` |
| DeepSeek-Prover-V1.5     | completion | 1024 | `deepseek-ai/DeepSeek-Prover-V1.5` |
| DeepSeek-Prover-V2-7B    | chat (reasoning) | 8192 | `deepseek-ai/DeepSeek-Prover-V2-7B` |
| Goedel-Prover-SFT        | completion | 1024 | `Goedel-LM/Goedel-Prover-SFT` |
| Kimina-Prover-Preview-Distill-7B | chat (reasoning) | 8192 | `AI-MO/Kimina-Prover-Preview-Distill-7B` |

All decoding uses temperature 0.6, top-p 0.95. Lean verification: 120-second
per-attempt timeout, 8-way sharded by `i mod 8`.

## Citation

```bibtex
@inproceedings{burton2026inference,
  title  = {Inference-Time Diversity in RL-Trained Lean Theorem Provers: A Diagnostic Study},
  author = {Burton, Zachary},
  booktitle = {ICML 2026 AI for Math Workshop},
  year   = {2026},
  eprint = {2601.16172},
  archivePrefix = {arXiv},
  primaryClass  = {cs.AI},
  url    = {https://arxiv.org/abs/2601.16172}
}
```

## License

MIT — see [LICENSE](LICENSE).
