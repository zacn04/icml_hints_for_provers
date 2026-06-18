#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Iterator, Any

import torch
from rich.console import Console

from autoform.model import Model
from autoform.ir import PerturbMode
from autoform.search import (
    run_oneshot,
    run_sample_k,
    run_search,
)

console = Console()

sys.path.insert(0, str(Path(__file__).parent))

print("ARGV:", sys.argv)

# ----------------------------
# Utilities
# ----------------------------

def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True).encode("utf-8")
    ).hexdigest()[:12]


def now_ms() -> int:
    return int(time.time() * 1000)


def git_commit_hash() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()[:12]
    except Exception:
        return "nogit"


def detect_gpus() -> Dict[str, Any]:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "-L"],
            stderr=subprocess.STDOUT,
        ).decode()
        gpus = [ln.strip() for ln in out.splitlines() if ln.strip()]
        return {
            "n_gpus": len(gpus),
            "gpus": gpus,
        }
    except Exception as e:
        return {
            "n_gpus": 0,
            "gpus": [],
            "err": str(e),
        }


def iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                yield json.loads(ln)


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


# ----------------------------
# CLI
# ----------------------------

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser("Lean F2F runner")

    # Core experiment axes
    ap.add_argument("--benchmark", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument(
        "--baseline",
        choices=["oneshot", "sample", "structured"],
        required=True,
    )
    ap.add_argument("--k", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--seed", type=int, default=1)

    # Model backend
    ap.add_argument(
        "--provider",
        choices=["hf", "ollama", "openai_compat"],
        default="hf",
    )
    ap.add_argument("--base-url", default="",
                     help="Base URL for openai_compat provider (default: env VLLM_BASE_URL)")

    # Perturbation mode (only for --baseline structured)
    ap.add_argument(
        "--perturbation",
        choices=["skeleton", "paraphrase", "comment", "goal_hint"],
        default="skeleton",
    )

    # Condition label for event logging
    ap.add_argument("--condition", default=None,
                     help="Human-readable condition label (e.g. A-RL, B-RL, C1, C2)")

    # Parallelism
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--num-shards", type=int, default=1)

    # Limits / output
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--output-root", default="outputs")
    ap.add_argument("--max-tokens", type=int, default=1024,
                    help="Max output tokens (bump for reasoning models like V2/Kimina)")

    return ap.parse_args()


# ----------------------------
# Main
# ----------------------------

def main() -> int:
    args = parse_args()

    torch.manual_seed(args.seed)

    bench_path = Path(args.benchmark)
    assert bench_path.exists(), bench_path

    perturb_mode = PerturbMode(args.perturbation)

    # Deterministic experiment identity
    exp_key = {
        "benchmark": bench_path.name,
        "model": args.model,
        "baseline": args.baseline,
        "perturbation": args.perturbation,
        "k": args.k,
        "timeout": args.timeout,
        "seed": args.seed,
        "shard": args.shard,
        "num_shards": args.num_shards,
    }
    exp_id = sha256_obj(exp_key)

    out_dir = Path(args.output_root) / exp_id
    ensure_dir(out_dir)
    events_path = out_dir / "events.jsonl"

    # Metadata header
    meta = {
        "event": "run_start",
        "ts_ms": now_ms(),
        "exp_id": exp_id,
        "exp_key": exp_key,
        "git": git_commit_hash(),
        "gpus": detect_gpus(),
        "argv": sys.argv,
    }
    with open(events_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(meta) + "\n")

    console.print(f"[bold]Experiment[/bold] {exp_id}")
    console.print(exp_key)

    # Load benchmark
    items = list(iter_jsonl(bench_path))

    # Sharding
    items = [
        it for i, it in enumerate(items)
        if i % args.num_shards == args.shard
    ]

    if args.limit:
        items = items[: args.limit]

    console.print(
        f"[cyan]Items[/cyan] {len(items)} "
        f"(shard {args.shard}/{args.num_shards})"
    )

    # Instantiate model
    # Use temperature > 0 for diverse sampling in pass@k experiments
    # DeepSeek-Prover papers use ~0.6-1.0
    temp = 0.0 if args.baseline == "oneshot" else 0.6

    model = Model(
        provider=args.provider,
        name=args.model,
        temperature=temp,
        max_tokens=args.max_tokens,
        base_url=args.base_url,
    )

    # ----------------------------
    # Run loop
    # ----------------------------

    for item in items:
        tid = item.get("id", "unknown")
        theorem = item["theorem"]
        context = item.get("context", "")

        trial_start = now_ms()

        # Create debug log directory for this theorem
        debug_log_dir = out_dir / "debug_logs" / tid
        debug_log_dir.mkdir(parents=True, exist_ok=True)

        try:
            if args.baseline == "oneshot":
                outcome = run_oneshot(
                    theorem=theorem,
                    context=context,
                    model=model,
                    timeout_sec=args.timeout,
                    seed=args.seed,
                    log_dir=debug_log_dir,
                )

            elif args.baseline == "sample":
                outcome = run_sample_k(
                    theorem=theorem,
                    context=context,
                    model=model,
                    k=args.k,
                    timeout_sec=args.timeout,
                    seed=args.seed,
                    log_dir=debug_log_dir,
                )

            elif args.baseline == "structured":
                outcome = run_search(
                    theorem=theorem,
                    context=context,
                    model=model,
                    k_variants=args.k,
                    timeout_sec=args.timeout,
                    seed=args.seed,
                    perturb_mode=perturb_mode,
                    log_dir=debug_log_dir,
                )

            else:
                raise ValueError(args.baseline)

            result = outcome.best

            if result.proved and outcome.proof_text:
                proof_path = out_dir / f"{tid}.lean"
                proof_path.write_text(outcome.proof_text)

            ev = {
                "event": "trial",
                "ts_ms": now_ms(),
                "theorem_id": tid,
                "model": args.model,
                "baseline": args.baseline,
                "perturbation_mode": args.perturbation,
                "condition": args.condition or f"{args.baseline}-{args.perturbation}",
                "k": args.k,
                "proved": result.proved,
                "compiled": result.compiled,
                "lean_attempts": outcome.attempts,
                "llm_calls": outcome.llm_calls,
                "time_ms": result.time_ms,
                "trial_time_ms": now_ms() - trial_start,
                "error_type": result.error_type,
                "attempt_results": [
                    {
                        "attempt_idx": ar.attempt_idx,
                        "skeleton_id": ar.skeleton_id,
                        "proved": ar.proved,
                        "compiled": ar.compiled,
                        "error_type": ar.error_type,
                    }
                    for ar in outcome.attempt_results
                ],
            }

        except Exception as e:
            ev = {
                "event": "trial_error",
                "ts_ms": now_ms(),
                "theorem_id": tid,
                "model": args.model,
                "baseline": args.baseline,
                "error": str(e)[:300],
                "trial_time_ms": now_ms() - trial_start,
            }

        with open(events_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev) + "\n")

    done = {
        "event": "run_end",
        "ts_ms": now_ms(),
        "exp_id": exp_id,
    }
    with open(events_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(done) + "\n")

    console.print("[green]DONE[/green]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
