#!/usr/bin/env python3
"""
Decision-procedure check for reviewer Lb8o:
of the +N NEW theorems B-RL k=16 solves that A-RL k=16 does not,
how many were closed by the injected tactic alone vs. needed the
model to extend the skeleton with further tactics?

Approach (per shard, pairing the same shard across A and B):
  1. Build A_solved[shard] and B_solved[shard] sets of theorem ids.
  2. NEW = B_solved \\ A_solved per shard.
  3. For each NEW theorem, find the successful B-RL attempt and look
     at (tactic_prefix, raw_output) from attempt_<NNN>.json.
  4. Classify the success as:
       - 'tactic-alone'   : the skeleton was a known one-shot closer
                            (simp, aesop, norm_num, nlinarith, ring,
                            linarith, ring_nf) AND the model's
                            raw_output is short / empty / closes immediately;
       - 'model-extended' : the model produced a substantive tactic
                            continuation beyond the skeleton.
  5. Report counts per shard and unioned across shards.
"""
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

ONE_SHOT_CLOSERS = {
    "simp", "aesop", "norm_num", "nlinarith", "ring",
    "linarith", "ring_nf",
}

# Body length below which we treat the model's continuation as
# 'no real extension' (close-enough to the closing tactic alone).
SHORT_OUTPUT_TOKEN_BUDGET = 8


def short_output(raw: str) -> bool:
    """Heuristic: 'short' = <=8 non-trivial tokens after stripping
    closers like done/rfl/sorry/trivial/by."""
    if not raw:
        return True
    # Strip markdown fences if present
    raw = re.sub(r"```.*", "", raw, flags=re.DOTALL).strip()
    # Drop trivially-closing tokens that aren't actually doing work
    tokens = [t for t in re.split(r"\s+", raw) if t]
    tokens = [t for t in tokens if t not in {"done", "rfl", "trivial", "by"}]
    return len(tokens) <= SHORT_OUTPUT_TOKEN_BUDGET


def first_skeleton_token(prefix):
    if not prefix:
        return "(empty)"
    return prefix[0].split()[0]


def collect_run(events_fp: Path):
    with open(events_fp) as f:
        return json.loads(f.readline()).get("exp_key", {})


def find_solved_theorems(debug_dir: Path, k: int):
    """Return {theorem_id: list of (attempt_idx, prefix, raw_output)}
    over successful attempts only."""
    out = defaultdict(list)
    if not debug_dir.is_dir():
        return out
    for thm in os.listdir(debug_dir):
        thm_dir = debug_dir / thm
        for i in range(k):
            rp = thm_dir / f"attempt_{i:03d}_result.json"
            ap = thm_dir / f"attempt_{i:03d}.json"
            if not (rp.exists() and ap.exists()):
                continue
            try:
                if not json.load(open(rp)).get("proved"):
                    continue
                attempt = json.load(open(ap))
            except Exception:
                continue
            out[thm].append((
                i,
                attempt.get("tactic_prefix", []),
                attempt.get("raw_output", ""),
            ))
    return out


def main():
    outputs = Path(os.environ.get("AUTOFORM_OUTPUTS", "outputs"))
    if not outputs.exists():
        print(f"{outputs} not found", file=sys.stderr)
        sys.exit(1)

    # Build per-shard sets for both conditions, indexed by shard.
    a_shards = {}  # shard -> {theorem -> list of (attempt, prefix, raw)}
    b_shards = {}
    for d in sorted(os.listdir(outputs)):
        events_fp = outputs / d / "events.jsonl"
        if not events_fp.exists():
            continue
        ek = collect_run(events_fp)
        if "RL" not in ek.get("model", ""):
            continue
        if ek.get("k") != 16:
            continue
        shard = ek.get("shard")
        debug = outputs / d / "debug_logs"
        if ek.get("baseline") == "sample":
            a_shards.setdefault(shard, []).append(find_solved_theorems(debug, 16))
        elif ek.get("baseline") == "structured":
            b_shards.setdefault(shard, []).append(find_solved_theorems(debug, 16))

    tactic_alone = 0
    model_extended = 0
    examples = {"tactic-alone": [], "model-extended": []}
    new_total = 0

    for shard in sorted(set(a_shards) | set(b_shards)):
        a_runs = a_shards.get(shard, [])
        b_runs = b_shards.get(shard, [])
        # Union A solves across (seed) runs in this shard
        a_set = set()
        for r in a_runs:
            a_set |= set(r.keys())
        # For B, average across (seed) runs: take theorems solved in
        # >=1 B run in this shard. Use the first successful attempt's
        # prefix/raw_output as the representative.
        b_thms = {}
        for r in b_runs:
            for thm, hits in r.items():
                if thm not in b_thms:
                    b_thms[thm] = hits[0]
        new_thms = set(b_thms) - a_set
        new_total += len(new_thms)
        for thm in sorted(new_thms):
            _, prefix, raw = b_thms[thm]
            head = first_skeleton_token(prefix)
            if head in ONE_SHOT_CLOSERS and short_output(raw):
                tactic_alone += 1
                bucket = "tactic-alone"
            else:
                model_extended += 1
                bucket = "model-extended"
            if len(examples[bucket]) < 5:
                examples[bucket].append({
                    "shard": shard,
                    "theorem": thm,
                    "prefix": prefix,
                    "raw_head": (raw[:120] + "...") if len(raw) > 120 else raw,
                })

    print("=== NEW solves: B-RL k=16 only vs A-RL k=16 (within-shard) ===")
    print(f"Total NEW solves (summed across shards x seeds):  {new_total}")
    print(f"  Closed by one-shot closer alone (heuristic):    {tactic_alone}")
    print(f"  Required model to extend the skeleton:          {model_extended}")
    if new_total:
        share = 100 * tactic_alone / new_total
        print(f"  Tactic-alone share: {share:.1f}%")
    print()
    for bucket, items in examples.items():
        print(f"--- examples: {bucket} ---")
        for it in items:
            print(f"  shard={it['shard']}  thm={it['theorem']}  prefix={it['prefix']}")
            print(f"    raw_head: {it['raw_head']!r}")
        print()


if __name__ == "__main__":
    main()
