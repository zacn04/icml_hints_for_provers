#!/usr/bin/env python3
"""
Per-skeleton solve breakdown for B-RL k=16 runs, within-shard counting.

Reads outputs/ exactly the way scripts/per_skeleton_analysis.py does: for
each shard with baseline='structured', model containing 'RL', k=16, walks
debug_logs/<theorem>/attempt_NNN.json to recover each attempt's tactic
prefix, maps it to one of the 15 skeleton IDs, and counts solves. Drops
attempt 15 (k=16 wraps the empty skeleton).
"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
matplotlib.rcParams['axes.spines.top'] = False
matplotlib.rcParams['axes.spines.right'] = False

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

SKELETON_TUPLES = [
    (),
    ("simp",),
    ("intro",),
    ("intros",),
    ("constructor",),
    ("refine ?_",),
    ("refine ⟨?_, ?_⟩",),
    ("aesop",),
    ("norm_num",),
    ("linarith",),
    ("nlinarith",),
    ("ring",),
    ("ring_nf",),
    ("simp", "try aesop"),
    ("simp", "try nlinarith"),
]

BLUE = '#4C72B0'
GREY = '#888888'


def skeleton_id(prefix):
    if not prefix:
        return 0
    tup = tuple(prefix)
    if tup in SKELETON_TUPLES:
        return SKELETON_TUPLES.index(tup)
    return None


def collect(outputs_dir: Path):
    """Return (per_skeleton_solved_per_shard, n_runs, theorems_per_shard_avg)."""
    solved_total = defaultdict(int)
    n_runs = 0
    total_solved_thms_per_shard = 0
    for d in sorted(os.listdir(outputs_dir)):
        events_fp = outputs_dir / d / "events.jsonl"
        if not events_fp.exists():
            continue
        with open(events_fp) as f:
            ek = json.loads(f.readline()).get("exp_key", {})
        if ek.get("baseline") != "structured":
            continue
        if "RL" not in ek.get("model", ""):
            continue
        if ek.get("k") != 16:
            continue

        debug_dir = outputs_dir / d / "debug_logs"
        if not debug_dir.is_dir():
            continue

        n_runs += 1
        shard_solvers = defaultdict(set)  # theorem -> {skeleton_id, ...}
        for thm in os.listdir(debug_dir):
            thm_dir = debug_dir / thm
            for i in range(15):  # drop attempt_015 (k=16 wrap)
                ap = thm_dir / f"attempt_{i:03d}.json"
                rp = thm_dir / f"attempt_{i:03d}_result.json"
                if not ap.exists() or not rp.exists():
                    continue
                with open(ap) as f:
                    prefix = json.load(f).get("tactic_prefix", [])
                with open(rp) as f:
                    res = json.load(f)
                sid = skeleton_id(prefix)
                if sid is None:
                    continue
                if res.get("proved"):
                    shard_solvers[thm].add(sid)

        total_solved_thms_per_shard += sum(1 for s in shard_solvers.values() if s)
        for thm, solvers in shard_solvers.items():
            for sid in solvers:
                solved_total[sid] += 1

    per_shard = {sid: solved_total[sid] / max(n_runs, 1) for sid in range(15)}
    return per_shard, n_runs, total_solved_thms_per_shard / max(n_runs, 1)


def plot(outputs_dir: Path, output_path: str):
    per_shard, n_runs, total_per_shard = collect(outputs_dir)
    if n_runs == 0:
        print("No B-RL k=16 runs found under", outputs_dir, file=sys.stderr)
        sys.exit(1)

    values = [per_shard[i] for i in range(15)]
    colors = [BLUE if i == 0 else GREY for i in range(15)]

    fig, ax = plt.subplots(figsize=(8.5, 4.0))
    bars = ax.bar(range(15), values, color=colors, edgecolor='#333', linewidth=0.6, width=0.7)

    for bar, v in zip(bars, values):
        if v > 0.02:
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.04,
                    f'{v:.2f}', ha='center', va='bottom',
                    fontsize=8.5, color='#333')

    ax.set_xticks(range(15))
    ax.set_xticklabels(SKELETONS, rotation=45, ha='right', fontsize=8.5)
    ax.set_ylabel(f'Theorems solved per shard\n(avg over {n_runs} shards)', fontsize=9.5)
    ax.set_title(
        f'Per-skeleton contribution to B-RL k=16 '
        f'(sum across all skeletons: {total_per_shard:.2f}/shard)',
        fontsize=11, fontweight='bold', pad=12,
    )
    ax.grid(axis='y', alpha=0.2, linestyle='--', linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_ylim(0, max(values) * 1.18)

    plt.tight_layout()
    fig.savefig(f'{output_path}.pdf', dpi=300, bbox_inches='tight')
    fig.savefig(f'{output_path}.png', dpi=200, bbox_inches='tight')
    print(f'Saved: {output_path}.pdf, {output_path}.png  ({n_runs} shards)')
    plt.close()


if __name__ == '__main__':
    here = Path(os.path.abspath(__file__)).parent
    os.chdir(here)
    outputs_dir = Path(os.environ.get('AUTOFORM_OUTPUTS', here.parent / 'outputs'))
    plot(outputs_dir, 'per_skeleton')
