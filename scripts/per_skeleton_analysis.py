#!/usr/bin/env python3
"""
Per-skeleton analysis for B-RL k=16 runs.

For each of the 15 skeletons, computes:
  - solved: number of theorems this skeleton proved (across all shards)
  - unique: number of theorems ONLY this skeleton proved within the same theorem's attempts

Aggregates across all 8 shards.
"""
import argparse
import json
import os
from collections import defaultdict

DEFAULT_OUTPUTS = os.environ.get("AUTOFORM_OUTPUTS", "outputs")
OUTPUTS = DEFAULT_OUTPUTS  # overridden by --outputs in main()

# Skeleton labels (must match TACTIC_SKELETONS in autoform/ir.py)
SKELETONS = [
    "(empty)",
    "simp",
    "intro",
    "intros",
    "constructor",
    "refine ?_",
    "refine <?_, ?_>",
    "aesop",
    "norm_num",
    "linarith",
    "nlinarith",
    "ring",
    "ring_nf",
    "simp; try aesop",
    "simp; try nlinarith",
]


def skeleton_id(prefix):
    """Map a tactic_prefix list to a skeleton index 0-14."""
    if not prefix:
        return 0
    tup = tuple(prefix)
    skeleton_tuples = [
        (),
        ("simp",),
        ("intro",),
        ("intros",),
        ("constructor",),
        ("refine ?_",),
        ("refine \u27e8?_, ?_\u27e9",),
        ("aesop",),
        ("norm_num",),
        ("linarith",),
        ("nlinarith",),
        ("ring",),
        ("ring_nf",),
        ("simp", "try aesop"),
        ("simp", "try nlinarith"),
    ]
    if tup in skeleton_tuples:
        return skeleton_tuples.index(tup)
    return None


def main():
    global OUTPUTS
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outputs", default=DEFAULT_OUTPUTS,
                    help=f"Runs directory (default: {DEFAULT_OUTPUTS}; env AUTOFORM_OUTPUTS)")
    args = ap.parse_args()
    OUTPUTS = args.outputs

    # Within-shard counting: each skeleton attempts each theorem exactly once
    # per shard (we drop attempt 15 to undo the k=16 wrap that double-counts
    # the empty skeleton). We sum per-shard solved/unique counts across shards
    # then divide to report a per-shard average.
    solved_total = defaultdict(int)
    unique_total = defaultdict(int)
    attempts_per_skeleton = defaultdict(int)
    n_runs = 0
    total_solved_thms_per_shard = 0  # for reporting average pass@16

    for d in sorted(os.listdir(OUTPUTS)):
        events_fp = os.path.join(OUTPUTS, d, "events.jsonl")
        if not os.path.exists(events_fp):
            continue
        with open(events_fp) as f:
            first = json.loads(f.readline())
        ek = first.get("exp_key", {})

        # Filter: B-RL k=16 only
        if ek.get("baseline") != "structured":
            continue
        if "RL" not in ek.get("model", ""):
            continue
        if ek.get("k") != 16:
            continue

        n_runs += 1
        debug_dir = os.path.join(OUTPUTS, d, "debug_logs")
        if not os.path.isdir(debug_dir):
            continue

        # Per-shard solver sets
        shard_solvers = defaultdict(set)
        for thm in os.listdir(debug_dir):
            thm_dir = os.path.join(debug_dir, thm)
            for i in range(15):  # drop attempt 15 (wrapped empty)
                af = os.path.join(thm_dir, f"attempt_{i:03d}.json")
                rf = os.path.join(thm_dir, f"attempt_{i:03d}_result.json")
                if not os.path.exists(af) or not os.path.exists(rf):
                    continue
                attempt = json.load(open(af))
                result = json.load(open(rf))
                prefix = attempt.get("tactic_prefix", [])
                sid = skeleton_id(prefix)
                if sid is None:
                    continue
                attempts_per_skeleton[sid] += 1
                if result.get("proved"):
                    shard_solvers[thm].add(sid)

        # Collapse this shard
        n_solved_this_shard = sum(1 for s in shard_solvers.values() if s)
        total_solved_thms_per_shard += n_solved_this_shard
        for thm, solvers in shard_solvers.items():
            for sid in solvers:
                solved_total[sid] += 1
            if len(solvers) == 1:
                unique_total[next(iter(solvers))] += 1

    print(f"Aggregated across {n_runs} B-RL k=16 shards (within-shard counting)")
    print(f"Average theorems solved per shard: {total_solved_thms_per_shard / max(n_runs,1):.1f}")
    print()

    print(f"{'#':>3} {'Skeleton':<22} {'Solved/shard':>13} {'Unique/shard':>13} {'Attempts':>10}")
    print("-" * 65)
    for sid in range(15):
        print(
            f"{sid:>3} {SKELETONS[sid]:<22} "
            f"{solved_total[sid]/max(n_runs,1):>13.2f} "
            f"{unique_total[sid]/max(n_runs,1):>13.2f} "
            f"{attempts_per_skeleton[sid]:>10}"
        )
    print()
    total_unique = sum(unique_total.values())
    total_solved = sum(solved_total.values())
    print(f"Sum of solved/shard: {total_solved/max(n_runs,1):.2f}")
    print(f"Sum of unique/shard: {total_unique/max(n_runs,1):.2f}")


if __name__ == "__main__":
    main()
