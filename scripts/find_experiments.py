#!/usr/bin/env python3
"""Helper script to find experiment runs by k_variants value."""
import json
import sys
from pathlib import Path

def find_experiments_by_k(base_log_dir: Path, target_k: int) -> list[Path]:
    """Find log directories for experiments with specific k_variants."""
    results = []
    
    if not base_log_dir.exists():
        return results
    
    # Search for all events.jsonl files
    for events_file in base_log_dir.rglob("events.jsonl"):
        log_dir = events_file.parent
        
        # Read run_start event to get config info
        with open(events_file, "r") as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    if event.get("event") == "run_start":
                        cfg_hash = event.get("cfg_hash", "")
                        # We can't directly get k from hash, but we can check configs
                        # For now, return the log dir - user will need to match manually
                        results.append((log_dir, cfg_hash))
                        break
                except json.JSONDecodeError:
                    continue
    
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python find_experiments.py <base_log_dir>")
        print("Example: python find_experiments.py outputs/logs/ir_search_v0/")
        sys.exit(1)
    
    base_dir = Path(sys.argv[1])
    experiments = find_experiments_by_k(base_dir, None)
    
    print(f"Found {len(experiments)} experiment runs:")
    print("-" * 80)
    for log_dir, cfg_hash in experiments:
        print(f"  Config hash: {cfg_hash}")
        print(f"  Log dir: {log_dir}")
        print()

if __name__ == "__main__":
    main()

