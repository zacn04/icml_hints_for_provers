#!/usr/bin/env python3
"""Venn diagram (A-RL vs B-RL at k=16) and 'sorry' analysis."""

import argparse
import json
import os
from pathlib import Path
from collections import defaultdict

DEFAULT_OUTPUTS = Path(os.environ.get("AUTOFORM_OUTPUTS", "outputs"))
OUTPUTS = DEFAULT_OUTPUTS  # overridden by --outputs in main()


def load_runs():
    """Load all run metadata from events.jsonl first lines."""
    runs = []
    for d in OUTPUTS.iterdir():
        if not d.is_dir():
            continue
        ev = d / "events.jsonl"
        if not ev.exists():
            continue
        with open(ev) as f:
            first = f.readline().strip()
            if not first:
                continue
            meta = json.loads(first)
        ek = meta.get("exp_key", {})
        runs.append({
            "dir": d,
            "baseline": ek.get("baseline"),
            "model": ek.get("model", ""),
            "k": ek.get("k"),
            "shard": ek.get("shard"),
        })
    return runs


def get_proved_theorems(run_dirs):
    """Return set of theorem names proved in any attempt across given dirs."""
    proved = set()
    for d in run_dirs:
        dl = d / "debug_logs"
        if not dl.exists():
            continue
        for thm_dir in dl.iterdir():
            if not thm_dir.is_dir():
                continue
            for f in thm_dir.glob("attempt_*_result.json"):
                try:
                    data = json.loads(f.read_text())
                    if data.get("proved"):
                        proved.add(thm_dir.name)
                        break  # no need to check more attempts for this theorem
                except (json.JSONDecodeError, OSError):
                    pass
    return proved


def sorry_analysis(run_dirs, label):
    """Check raw_output for 'sorry' in attempt JSONs."""
    total = 0
    sorry_count = 0
    examples = []
    for d in run_dirs:
        dl = d / "debug_logs"
        if not dl.exists():
            continue
        for thm_dir in dl.iterdir():
            if not thm_dir.is_dir():
                continue
            for f in sorted(thm_dir.glob("attempt_[0-9]*.json")):
                # skip _result.json and _reconstructed.lean
                if "_result" in f.name or "_reconstructed" in f.name:
                    continue
                try:
                    data = json.loads(f.read_text())
                except (json.JSONDecodeError, OSError):
                    continue
                raw = data.get("raw_output", "")
                total += 1
                if "sorry" in raw:
                    sorry_count += 1
                    if len(examples) < 5:
                        examples.append({
                            "theorem": thm_dir.name,
                            "file": f.name,
                            "snippet": raw[:200],
                        })
    print(f"\n=== Sorry analysis: {label} ===")
    print(f"Total attempts checked: {total}")
    print(f"Attempts containing 'sorry': {sorry_count} ({100*sorry_count/max(total,1):.1f}%)")
    if examples:
        print("Examples:")
        for ex in examples:
            print(f"  {ex['theorem']}/{ex['file']}:")
            print(f"    {ex['snippet']!r}")
    else:
        print("No examples of 'sorry' found.")


def main():
    global OUTPUTS
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outputs", default=str(DEFAULT_OUTPUTS),
                    help=f"Runs directory (default: {DEFAULT_OUTPUTS}; env AUTOFORM_OUTPUTS)")
    args = ap.parse_args()
    OUTPUTS = Path(args.outputs)

    runs = load_runs()

    # Classify runs
    a_rl_k16 = [r["dir"] for r in runs if r["baseline"] == "sample" and "RL" in r["model"] and r["k"] == 16]
    b_rl_k16 = [r["dir"] for r in runs if r["baseline"] == "structured" and "RL" in r["model"] and r["k"] == 16]
    base_runs = [r["dir"] for r in runs if "Base" in r["model"] or "base" in r["model"].lower()]

    print(f"A-RL k=16 run dirs: {len(a_rl_k16)}")
    print(f"B-RL k=16 run dirs: {len(b_rl_k16)}")
    print(f"Base model run dirs: {len(base_runs)}")

    # --- Analysis 1: Venn ---
    proved_a = get_proved_theorems(a_rl_k16)
    proved_b = get_proved_theorems(b_rl_k16)

    only_a = proved_a - proved_b
    only_b = proved_b - proved_a
    both = proved_a & proved_b

    print("\n=== Venn Diagram: A-RL k=16 vs B-RL k=16 ===")
    print(f"|A-RL only|  = {len(only_a)}")
    print(f"|B-RL only|  = {len(only_b)}")
    print(f"|A ∩ B|      = {len(both)}")
    print(f"|A-RL total| = {len(proved_a)}")
    print(f"|B-RL total| = {len(proved_b)}")

    print(f"\nA-RL only ({len(only_a)}):")
    for t in sorted(only_a):
        print(f"  {t}")
    print(f"\nB-RL only ({len(only_b)}):")
    for t in sorted(only_b):
        print(f"  {t}")
    print(f"\nA ∩ B ({len(both)}):")
    for t in sorted(both):
        print(f"  {t}")

    # --- Analysis 2: Sorry ---
    sorry_analysis(b_rl_k16, "B-RL k=16")
    sorry_analysis(base_runs, "Base models (all)")


if __name__ == "__main__":
    main()
