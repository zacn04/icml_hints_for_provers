#!/usr/bin/env python3
"""Smoke test for model backend."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from autoform.model import Model

def main():
    # Test HF backend (adjust model name as needed)
    model = Model(
        provider="hf",
        name="deepseek-ai/DeepSeek-Prover-V2-7B", 
        temperature=0.2,
        max_tokens=128,
    )
    
    theorem = "theorem t : True := by"
    print(f"Testing with theorem: {theorem}")
    print("=" * 80)
    
    output = model.generate(theorem, seed=42)
    
    print("\nRaw model output:")
    print(output)
    print("=" * 80)
    
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

