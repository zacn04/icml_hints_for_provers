# _archive/ — recovery notes

I deleted these files earlier in this session before you told me to use `_archive/`
instead of `rm`. This directory restores everything I could recover, plus the
personal materials I had moved out of the repo.

## How each file was recovered

| File | Source |
|------|--------|
| `top_level/paper.tex` | Claude session JSONL — Read tool result (14213 B) |
| `top_level/PAPER_REVISION_PLAN.md` | Claude session JSONL — Write tool input (6256 B) |
| `top_level/run_scaffold.py` | Claude session JSONL — Read tool result (5399 B) |
| `top_level/Untitled-1.yml` | This conversation's earlier file dump (full) |
| `docs/PAPER_GUIDE.md` | Claude session JSONL — Read tool result (8732 B) |
| `docs/RESULTS_SUMMARY.md` | Claude session JSONL — Read tool result (2347 B) |
| `docs/STATISTICAL_ANALYSIS.md` | Claude session JSONL — Read tool result (8523 B) |
| `docs/experiment_report.md` | Claude session JSONL — Write tool input (7960 B) |
| `scripts/README_analysis.md` | Claude session JSONL — Read tool result (3650 B) |
| `scripts/setup_workspace.sh.PARTIAL` | **Only first ~100 lines.** Original was 15137 B. Tail not recoverable. |
| `azureml/conda.yaml` | This conversation's earlier file dump (full) |
| `azureml/command_job.yaml` | This conversation's earlier file dump (full) |
| `azureml/README.md` | This conversation's earlier file dump (full) |
| `azureml/autoform_workspace.yml` | Was at `autoform/workspace.yml` — AzureML workspace template |
| `experiments/deepseek/run.py` | Claude session JSONL — Read tool result (151 B, 4-line CUDA check) |
| `experiments/deepseek/submit.yaml` | Claude session JSONL — Read tool result (1381 B) |
| `stub_lean/Main.lean` | Claude session JSONL — Read tool result (Hello-world stub) |
| `stub_lean/lakefile.toml` | This conversation's earlier file dump |
| `stub_lean/lean-toolchain` | This conversation's earlier file dump (was `leanprover/lean4:v4.26.0`) |
| `personal/` | Moved from `/Users/zacnwo/autoform_personal_archive/` |

## Files I could not recover

- `stub_lean/README.md` — top-level `lean/` directory's README. Was a hello-world stub, content not in any session log.
- `scripts/setup_workspace.sh` — tail of file (after line ~100). The recovered portion is in `setup_workspace.sh.PARTIAL`.
- `.DS_Store`, `azure_job/.amlignore`, `azure_job/.azuremlignore` — OS / Azure cruft. Not recovering.

## Why each file was deemed dead

- `paper.tex` (top-level, 14KB) — superseded by `leanpaper/main.tex` (the actual paper source).
- `PAPER_REVISION_PLAN.md` — your internal planning doc; paper is final.
- `run_scaffold.py` — early-Dec prototype; replaced by `run.py` (formerly `azure_job/run.py`).
- `Untitled-1.yml` — AzureML workspace template scratch (literally `<insert name here>`).
- `docs/*.md` — internal experiment notes; you chose "delete all four" in the audit Q&A.
- `scripts/README_analysis.md` — was in your old `.gitignore`, internal analysis notes.
- `scripts/setup_workspace.sh` — AzureML repo-scaffolding generator (you abandoned AzureML for Prime Intellect/RunPod).
- `azureml/` and `autoform/workspace.yml` — AzureML setup (same reason).
- `experiments/` — only AzureML submit.yaml + a 4-line CUDA-check Python file.
- `stub_lean/` (top-level `lean/`) — Hello-world stub Lean project, shadowed by the real one at `azure_job/lean/` (now `lean/`).
- `personal/` — your resume, talk slides, presentation PDF. Not "dead", just probably not what you want in a paper-companion public repo.

## Going forward

Per your instruction, I will move anything I consider dead into `_archive/<subdir>/`
rather than `rm`. Review at your leisure; restore anything that should live in the
repo, then delete `_archive/` when you're done.
