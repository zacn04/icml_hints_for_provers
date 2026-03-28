#!/usr/bin/env python3
"""
Statistical significance analysis for IR search experiments.

Compares proof success rates across different k_variants values.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from scipy import stats


def load_events(log_dir: Path) -> List[Dict]:
    """Load all events from a log directory."""
    events_path = log_dir / "events.jsonl"
    if not events_path.exists():
        return []
    
    events = []
    with open(events_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def extract_trials(events: List[Dict]) -> List[Dict]:
    """Extract trial events only."""
    return [e for e in events if e.get("event") == "trial"]


def get_k_from_config_hash(cfg_hash: str, configs_dir: Path) -> int | None:
    """Try to infer k_variants from config hash by checking config files."""
    # This is approximate - in practice you'd store k in events or match configs
    # For now, we'll require k to be passed explicitly
    return None


def aggregate_by_theorem_seed(trials: List[Dict]) -> Dict[Tuple[str, int], Dict]:
    """Aggregate trials by (theorem_id, seed)."""
    aggregated = {}
    for trial in trials:
        key = (trial["theorem_id"], trial["seed"])
        # Keep best result if multiple trials (shouldn't happen, but be safe)
        if key not in aggregated:
            aggregated[key] = trial
        elif trial.get("proved", False) and not aggregated[key].get("proved", False):
            aggregated[key] = trial
    return aggregated


def compare_k_values(
    log_dirs: Dict[int, Path],
    configs_dir: Path,
) -> Dict:
    """
    Compare success rates across different k values.
    
    Args:
        log_dirs: Dict mapping k_variants -> log directory path
        configs_dir: Directory containing config files
    
    Returns:
        Dictionary with statistical test results
    """
    # Load all trials
    all_trials = {}
    for k, log_dir in log_dirs.items():
        events = load_events(log_dir)
        trials = extract_trials(events)
        all_trials[k] = aggregate_by_theorem_seed(trials)
    
    # Find common (theorem_id, seed) pairs across all k values
    all_keys = set()
    for trials in all_trials.values():
        all_keys.update(trials.keys())
    
    # Build comparison matrix: (theorem_id, seed) -> {k: proved}
    comparison_data = {}
    for key in all_keys:
        comparison_data[key] = {}
        for k in log_dirs.keys():
            proved = all_trials[k].get(key, {}).get("proved", False)
            comparison_data[key][k] = proved
    
    # Statistical tests
    results = {}
    
    # 1. Overall success rates
    for k in sorted(log_dirs.keys()):
        proved_count = sum(1 for data in comparison_data.values() if data.get(k, False))
        total = len(comparison_data)
        results[f"k={k}_success_rate"] = {
            "proved": proved_count,
            "total": total,
            "rate": proved_count / total if total > 0 else 0.0,
        }
    
    # 2. Paired comparison: k=1 vs k>1 (McNemar's test)
    if 1 in log_dirs.keys():
        k1_data = []
        k_other_data = []
        paired_data = []
        
        for k_other in sorted(log_dirs.keys()):
            if k_other == 1:
                continue
            
            # Build 2x2 contingency table for McNemar's test
            # Both fail, k1 fails k_other succeeds, k1 succeeds k_other fails, both succeed
            contingency = [[0, 0], [0, 0]]
            
            for key, data in comparison_data.items():
                k1_result = data.get(1, False)
                k_other_result = data.get(k_other, False)
                
                if not k1_result and not k_other_result:
                    contingency[0][0] += 1
                elif not k1_result and k_other_result:
                    contingency[0][1] += 1
                elif k1_result and not k_other_result:
                    contingency[1][0] += 1
                else:  # both succeed
                    contingency[1][1] += 1
            
            # McNemar's test (for paired binary data)
            # Only uses discordant pairs (cells [0][1] and [1][0])
            discordant = contingency[0][1] + contingency[1][0]
            if discordant > 0:
                # McNemar's chi-square statistic
                b = contingency[0][1]  # k1 fails, k_other succeeds
                c = contingency[1][0]  # k1 succeeds, k_other fails
                
                # Continuity correction
                chi2 = ((abs(b - c) - 1) ** 2) / (b + c) if (b + c) > 0 else 0
                p_value = 1 - stats.chi2.cdf(chi2, df=1) if (b + c) > 0 else 1.0
                
                # Effect size: improvement rate
                improvement_rate = (b - c) / discordant if discordant > 0 else 0
                absolute_improvement = b / len(comparison_data) if len(comparison_data) > 0 else 0
            else:
                chi2 = 0
                p_value = 1.0
                improvement_rate = 0
                absolute_improvement = 0
            
            results[f"k1_vs_k{k_other}"] = {
                "contingency_table": contingency,
                "discordant_pairs": discordant,
                "k1_fails_k_other_succeeds": contingency[0][1],
                "k1_succeeds_k_other_fails": contingency[1][0],
                "chi2_statistic": chi2,
                "p_value": p_value,
                "improvement_rate": improvement_rate,
                "absolute_improvement": absolute_improvement,
                "significant": p_value < 0.05,
            }
    
    # 3. Trend analysis: success rate vs k
    k_values = sorted(log_dirs.keys())
    success_rates = [results[f"k={k}_success_rate"]["rate"] for k in k_values]
    
    if len(k_values) >= 3:
        # Spearman correlation (monotonic relationship)
        spearman_corr, spearman_p = stats.spearmanr(k_values, success_rates)
        results["trend_analysis"] = {
            "spearman_correlation": spearman_corr,
            "spearman_p_value": spearman_p,
            "monotonic_increase": spearman_corr > 0 and spearman_p < 0.05,
        }
    
    # 4. Per-theorem analysis (aggregate across seeds)
    theorem_results = defaultdict(lambda: defaultdict(int))
    for key, data in comparison_data.items():
        theorem_id, seed = key
        for k, proved in data.items():
            theorem_results[theorem_id][k] += int(proved)
    
    # Count theorems where k>1 helps
    theorems_helped = 0
    theorems_hurt = 0
    theorems_unchanged = 0
    
    if 1 in log_dirs.keys():
        for theorem_id, k_results in theorem_results.items():
            k1_best = k_results.get(1, 0) > 0  # Any seed succeeded
            k_other_best = any(
                k_results.get(k, 0) > 0
                for k in log_dirs.keys()
                if k != 1
            )
            
            if not k1_best and k_other_best:
                theorems_helped += 1
            elif k1_best and not k_other_best:
                theorems_hurt += 1
            else:
                theorems_unchanged += 1
    
    results["per_theorem_analysis"] = {
        "theorems_helped_by_k_variants": theorems_helped,
        "theorems_hurt_by_k_variants": theorems_hurt,
        "theorems_unchanged": theorems_unchanged,
        "total_theorems": len(theorem_results),
    }
    
    return results


def print_results(results: Dict):
    """Pretty print statistical results."""
    print("=" * 80)
    print("STATISTICAL SIGNIFICANCE ANALYSIS")
    print("=" * 80)
    
    # Success rates
    print("\n1. SUCCESS RATES BY K:")
    print("-" * 80)
    for key in sorted(results.keys()):
        if key.startswith("k=") and key.endswith("_success_rate"):
            k = key.split("=")[1].split("_")[0]
            data = results[key]
            print(f"  k={k:3s}: {data['proved']:4d}/{data['total']:4d} = {data['rate']:.1%}")
    
    # Paired comparisons
    print("\n2. PAIRED COMPARISONS (k=1 vs k>1):")
    print("-" * 80)
    for key in sorted(results.keys()):
        if key.startswith("k1_vs_k"):
            k_other = key.split("k")[-1]
            data = results[key]
            print(f"\n  k=1 vs k={k_other}:")
            print(f"    Contingency table:")
            print(f"      [k1 fails, k{k_other} fails] = {data['contingency_table'][0][0]}")
            print(f"      [k1 fails, k{k_other} succeeds] = {data['contingency_table'][0][1]}")
            print(f"      [k1 succeeds, k{k_other} fails] = {data['contingency_table'][1][0]}")
            print(f"      [k1 succeeds, k{k_other} succeeds] = {data['contingency_table'][1][1]}")
            print(f"    McNemar's test:")
            print(f"      χ² = {data['chi2_statistic']:.4f}")
            print(f"      p-value = {data['p_value']:.6f}")
            print(f"      {'✓ SIGNIFICANT' if data['significant'] else '✗ NOT SIGNIFICANT'} (α=0.05)")
            print(f"    Effect size:")
            print(f"      Absolute improvement: {data['absolute_improvement']:.1%}")
            print(f"      Improvement rate (discordant pairs): {data['improvement_rate']:.1%}")
    
    # Trend analysis
    if "trend_analysis" in results:
        print("\n3. TREND ANALYSIS:")
        print("-" * 80)
        trend = results["trend_analysis"]
        print(f"  Spearman correlation: {trend['spearman_correlation']:.4f}")
        print(f"  p-value: {trend['spearman_p_value']:.6f}")
        print(f"  Monotonic increase: {'✓ YES' if trend['monotonic_increase'] else '✗ NO'}")
    
    # Per-theorem analysis
    if "per_theorem_analysis" in results:
        print("\n4. PER-THEOREM ANALYSIS:")
        print("-" * 80)
        per_thm = results["per_theorem_analysis"]
        print(f"  Theorems helped by k-variants: {per_thm['theorems_helped_by_k_variants']}")
        print(f"  Theorems hurt by k-variants: {per_thm['theorems_hurt_by_k_variants']}")
        print(f"  Theorems unchanged: {per_thm['theorems_unchanged']}")
        print(f"  Total theorems: {per_thm['total_theorems']}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Analyze statistical significance of k-variants experiments"
    )
    ap.add_argument(
        "--log-dirs",
        required=True,
        nargs="+",
        help="Space-separated list of log directories (one per k value)",
    )
    ap.add_argument(
        "--k-values",
        required=True,
        type=int,
        nargs="+",
        help="Space-separated list of k_variants values (must match log-dirs order)",
    )
    ap.add_argument(
        "--output",
        type=str,
        help="Optional: save results to JSON file",
    )
    
    args = ap.parse_args()
    
    if len(args.log_dirs) != len(args.k_values):
        print("ERROR: Number of log-dirs must match number of k-values", file=sys.stderr)
        return 1
    
    # Build log directory mapping
    log_dirs = {}
    for k, log_dir_str in zip(args.k_values, args.log_dirs):
        log_dir = Path(log_dir_str)
        if not log_dir.exists():
            print(f"WARNING: Log directory does not exist: {log_dir}", file=sys.stderr)
            continue
        log_dirs[k] = log_dir
    
    if not log_dirs:
        print("ERROR: No valid log directories found", file=sys.stderr)
        return 1
    
    # Find configs directory (assume it's at repo root)
    configs_dir = Path(__file__).parent.parent / "configs"
    
    # Run analysis
    results = compare_k_values(log_dirs, configs_dir)
    
    # Print results
    print_results(results)
    
    # Save if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

