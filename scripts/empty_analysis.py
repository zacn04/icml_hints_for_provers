#!/usr/bin/env python3
"""
Compute pass@k metrics for the empty skeleton:

1. B-RL k=16 runs (baseline="structured"): For each shard, find which theorems
   attempt_000 (tactic_prefix=[]) solved. Report per-shard count and the union
   across all shards.

2. A-RL k=16 runs (baseline="sample"): Report total unique theorems solved
   (this is pass@16 of pure empty sampling).
"""
import argparse
import json
import os
from collections import defaultdict

DEFAULT_OUTPUTS = os.environ.get("AUTOFORM_OUTPUTS", "outputs")
OUTPUTS = DEFAULT_OUTPUTS  # overridden by --outputs in main()


def load_exp_key(run_dir):
    events_fp = os.path.join(run_dir, "events.jsonl")
    if not os.path.exists(events_fp):
        return None
    with open(events_fp) as f:
        return json.loads(f.readline()).get("exp_key", {})


def main():
    global OUTPUTS
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outputs", default=DEFAULT_OUTPUTS,
                    help=f"Runs directory (default: {DEFAULT_OUTPUTS}; env AUTOFORM_OUTPUTS)")
    args = ap.parse_args()
    OUTPUTS = args.outputs

    # ---- B-RL k=16: empty skeleton analysis ----
    print("=" * 70)
    print("B-RL k=16: Empty skeleton (attempt_000, tactic_prefix=[]) analysis")
    print("=" * 70)

    # Collect per-shard data
    # Key: (run_id) -> set of theorems solved by empty skeleton
    brl_runs = []
    brl_empty_solved_per_run = {}
    brl_all_solved_per_run = {}

    for d in sorted(os.listdir(OUTPUTS)):
        run_dir = os.path.join(OUTPUTS, d)
        ek = load_exp_key(run_dir)
        if ek is None:
            continue
        if ek.get("baseline") != "structured":
            continue
        if "RL" not in ek.get("model", ""):
            continue
        if ek.get("k") != 16:
            continue

        debug_dir = os.path.join(run_dir, "debug_logs")
        if not os.path.isdir(debug_dir):
            continue

        shard = ek.get("shard", "?")
        seed = ek.get("seed", "?")
        brl_runs.append((d, shard, seed))

        empty_solved = set()
        all_solved = set()

        for thm in os.listdir(debug_dir):
            thm_dir = os.path.join(debug_dir, thm)
            if not os.path.isdir(thm_dir):
                continue

            # Check attempt_000 specifically
            af = os.path.join(thm_dir, "attempt_000.json")
            rf = os.path.join(thm_dir, "attempt_000_result.json")
            if os.path.exists(af) and os.path.exists(rf):
                with open(af) as f:
                    attempt = json.load(f)
                with open(rf) as f:
                    result = json.load(f)
                prefix = attempt.get("tactic_prefix", [])
                if prefix == [] and result.get("proved"):
                    empty_solved.add(thm)

            # Check all attempts for total solved
            for fname in os.listdir(thm_dir):
                if fname.endswith("_result.json"):
                    rf2 = os.path.join(thm_dir, fname)
                    with open(rf2) as f:
                        r = json.load(f)
                    if r.get("proved"):
                        all_solved.add(thm)
                        break

        brl_empty_solved_per_run[d] = empty_solved
        brl_all_solved_per_run[d] = all_solved

    # Report per-run
    print(f"\n{'Run ID':<15} {'Shard':>5} {'Seed':>4} {'Empty solved':>13} {'All solved':>11}")
    print("-" * 55)
    for d, shard, seed in sorted(brl_runs, key=lambda x: (x[1], x[2])):
        print(f"{d:<15} {shard:>5} {seed:>4} {len(brl_empty_solved_per_run[d]):>13} {len(brl_all_solved_per_run[d]):>11}")

    # Union across all shards
    union_empty = set()
    union_all = set()
    for d, _, _ in brl_runs:
        union_empty |= brl_empty_solved_per_run[d]
        union_all |= brl_all_solved_per_run[d]

    avg_empty = sum(len(brl_empty_solved_per_run[d]) for d, _, _ in brl_runs) / max(len(brl_runs), 1)
    avg_all = sum(len(brl_all_solved_per_run[d]) for d, _, _ in brl_runs) / max(len(brl_runs), 1)

    print(f"\nAverage empty solved per shard: {avg_empty:.2f}")
    print(f"Average all solved per shard:   {avg_all:.2f}")
    print(f"\nUnion of empty solved across all {len(brl_runs)} B-RL runs: {len(union_empty)}")
    print(f"Union of all solved across all {len(brl_runs)} B-RL runs:   {len(union_all)}")

    # Also break down by shard (union across seeds within same shard)
    shard_empty = defaultdict(set)
    shard_all = defaultdict(set)
    for d, shard, seed in brl_runs:
        shard_empty[shard] |= brl_empty_solved_per_run[d]
        shard_all[shard] |= brl_all_solved_per_run[d]

    print(f"\nPer-shard union (across seeds):")
    print(f"{'Shard':>5} {'Empty union':>12} {'All union':>10}")
    for s in sorted(shard_empty.keys()):
        print(f"{s:>5} {len(shard_empty[s]):>12} {len(shard_all[s]):>10}")

    # ---- A-RL k=16: pure sampling ----
    print("\n" + "=" * 70)
    print("A-RL k=16: Pure sampling (baseline='sample') analysis")
    print("=" * 70)

    arl_runs = []
    arl_solved_per_run = {}

    for d in sorted(os.listdir(OUTPUTS)):
        run_dir = os.path.join(OUTPUTS, d)
        ek = load_exp_key(run_dir)
        if ek is None:
            continue
        if ek.get("baseline") != "sample":
            continue
        if "RL" not in ek.get("model", ""):
            continue
        if ek.get("k") != 16:
            continue

        debug_dir = os.path.join(run_dir, "debug_logs")
        if not os.path.isdir(debug_dir):
            continue

        shard = ek.get("shard", "?")
        seed = ek.get("seed", "?")
        arl_runs.append((d, shard, seed))

        solved = set()
        for thm in os.listdir(debug_dir):
            thm_dir = os.path.join(debug_dir, thm)
            if not os.path.isdir(thm_dir):
                continue
            for fname in os.listdir(thm_dir):
                if fname.endswith("_result.json"):
                    rf = os.path.join(thm_dir, fname)
                    with open(rf) as f:
                        r = json.load(f)
                    if r.get("proved"):
                        solved.add(thm)
                        break

        arl_solved_per_run[d] = solved

    print(f"\n{'Run ID':<15} {'Shard':>5} {'Seed':>4} {'Solved':>7}")
    print("-" * 35)
    for d, shard, seed in sorted(arl_runs, key=lambda x: (x[1], x[2])):
        print(f"{d:<15} {shard:>5} {seed:>4} {len(arl_solved_per_run[d]):>7}")

    union_arl = set()
    for d, _, _ in arl_runs:
        union_arl |= arl_solved_per_run[d]

    avg_arl = sum(len(arl_solved_per_run[d]) for d, _, _ in arl_runs) / max(len(arl_runs), 1)
    print(f"\nAverage solved per shard: {avg_arl:.2f}")
    print(f"Union across all {len(arl_runs)} A-RL runs: {len(union_arl)}")

    # Shard-level union
    shard_arl = defaultdict(set)
    for d, shard, seed in arl_runs:
        shard_arl[shard] |= arl_solved_per_run[d]
    print(f"\nPer-shard union (across seeds):")
    for s in sorted(shard_arl.keys()):
        print(f"  Shard {s}: {len(shard_arl[s])}")

    # ---- Comparison ----
    print("\n" + "=" * 70)
    print("Comparison")
    print("=" * 70)
    print(f"B-RL empty skeleton union (pass@24 of empty): {len(union_empty)}")
    print(f"A-RL union (pass@16 per shard, {len(arl_runs)} shards):  {len(union_arl)}")
    if union_empty and union_arl:
        overlap = union_empty & union_arl
        only_brl = union_empty - union_arl
        only_arl = union_arl - union_empty
        print(f"Overlap: {len(overlap)}")
        print(f"Only in B-RL empty: {len(only_brl)} -> {only_brl}")
        print(f"Only in A-RL: {len(only_arl)} -> {only_arl}")


if __name__ == "__main__":
    main()
