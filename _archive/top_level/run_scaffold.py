#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterator

import yaml
from rich.console import Console

from autoform.model import Model
from autoform.search import run_search

console = Console()

def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]

def git_commit_hash() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode().strip()[:12]
    except Exception:
        return "nogit"

def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def iter_jsonl(path: str) -> Iterator[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def now_ms() -> int:
    return int(time.time() * 1000)

def detect_gpus() -> Dict[str, Any]:
    try:
        out = subprocess.check_output(["nvidia-smi", "-L"], stderr=subprocess.STDOUT).decode()
        gpus = [ln.strip() for ln in out.splitlines() if ln.strip()]
        return {"n_gpus": len(gpus), "gpus": gpus[:16]}
    except Exception as e:
        return {"n_gpus": 0, "gpus": [], "err": str(e)}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    cfg = load_yaml(args.config)
    cfg_raw = json.dumps(cfg, sort_keys=True)
    cfg_hash = sha256_str(cfg_raw)

    exp = cfg["experiment"]
    bench = cfg["benchmark"]
    seeds = exp.get("seeds", [1])

    out_dir = Path(exp["output_dir"]) / exp["name"] / cfg_hash
    log_dir = Path(exp["log_dir"]) / exp["name"] / cfg_hash
    ensure_dir(out_dir)
    ensure_dir(log_dir)

    events_path = log_dir / "events.jsonl"

    limit = args.limit if args.limit is not None else exp.get("limit", None)

    meta = {
        "ts_ms": now_ms(),
        "event": "run_start",
        "cfg_hash": cfg_hash,
        "git": git_commit_hash(),
        "gpus": detect_gpus(),
        "argv": sys.argv,
    }
    with open(events_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(meta) + "\n")

    items = list(iter_jsonl(bench["path"]))
    start = int(bench.get("start", 0))
    count = bench.get("count", None)
    items = items[start:] if start else items
    if count is not None:
        items = items[: int(count)]
    if limit is not None:
        items = items[: int(limit)]

    console.print(f"[bold]Run[/bold] {exp['name']} cfg={cfg_hash} items={len(items)} seeds={len(seeds)}")
    console.print(f"logs: {events_path}")

    # Instantiate model from config
    model_cfg = cfg["model"]
    model = Model(
        provider=model_cfg.get("provider", "ollama"),
        name=model_cfg["name"],
        temperature=model_cfg["temperature"],
        max_tokens=model_cfg["max_tokens"],
    )
    
    search_cfg = cfg["search"]
    lean_cfg = cfg["lean"]

    for item in items:
        tid = item.get("id", "unknown")
        theorem = item.get("theorem", "")
        context = item.get("context", "")
        
        for seed in seeds:
            trial_start_ms = now_ms()
            
            try:
                outcome = run_search(
                    theorem=theorem,
                    context=context,
                    model=model,
                    seed=seed,
                    k_variants=search_cfg["k_variants"],
                    timeout_sec=lean_cfg["timeout_sec"],
                )
                
                result = outcome.best
                
                # Save successful proof
                if result.proved and outcome.proof_text:
                    proof_file = out_dir / f"{tid}_seed{seed}.lean"
                    proof_file.write_text(outcome.proof_text)
                
                ev = {
                    "ts_ms": now_ms(),
                    "event": "trial",
                    "theorem_id": tid,
                    "seed": seed,
                    "proved": result.proved,
                    "compiled": result.compiled,
                    "attempts": outcome.attempts,
                    "time_ms": result.time_ms,
                    "error_type": result.error_type,
                    "trial_time_ms": now_ms() - trial_start_ms,
                }
            except Exception as e:
                ev = {
                    "ts_ms": now_ms(),
                    "event": "trial_error",
                    "theorem_id": tid,
                    "seed": seed,
                    "error": str(e)[:200],
                    "trial_time_ms": now_ms() - trial_start_ms,
                }
            
            with open(events_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(ev) + "\n")

    done = {"ts_ms": now_ms(), "event": "run_end", "cfg_hash": cfg_hash}
    with open(events_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(done) + "\n")

    console.print("[green]OK[/green] run completed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())