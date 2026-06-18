#!/usr/bin/env python3
import os
import subprocess
import sys

def main() -> int:
    print("Sanity check: run scaffold with limit=1")
    # Use run_scaffold.py if it exists, otherwise run.py
    entrypoint = "run_scaffold.py" if os.path.exists("run_scaffold.py") else "run.py"
    cmd = [sys.executable, entrypoint, "--config", "configs/ir_search.yaml", "--limit", "1"]
    print("+", " ".join(cmd))
    subprocess.check_call(cmd)
    print("OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())