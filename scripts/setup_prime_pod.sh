#!/usr/bin/env bash
# setup_prime_pod.sh — Bootstrap a Prime Intellect A100 pod for batch inference.
#
# Usage (on the pod after SSH):
#   curl -sSL <your-repo-url>/scripts/setup_prime_pod.sh | bash
#   OR: git clone <repo> && cd autoform && bash scripts/setup_prime_pod.sh
#
# What it does:
#   1. Installs vLLM + dependencies
#   2. Installs elan + Lean v4.9.0-rc1
#   3. Builds the Lean project (downloads mathlib cache)
#   4. Pulls both DeepSeek-Prover models
#   5. Prints instructions to start the experiment

set -euo pipefail

echo "=== Prime Intellect Pod Setup ==="
echo "  Started: $(date)"
echo ""

# -------------------------------------------
# 1. Python dependencies
# -------------------------------------------
echo "[1/5] Installing Python dependencies..."
pip install --quiet vllm rich pyyaml

# -------------------------------------------
# 2. Lean toolchain (v4.9.0-rc1)
# -------------------------------------------
echo "[2/5] Installing Lean v4.9.0-rc1..."
if ! command -v elan &>/dev/null; then
    curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh -s -- -y --default-toolchain none
fi
export PATH="$HOME/.elan/bin:$PATH"
elan toolchain install leanprover/lean4:v4.9.0-rc1
elan default leanprover/lean4:v4.9.0-rc1
echo "  Lean version: $(lean --version 2>/dev/null || echo 'installed')"

# -------------------------------------------
# 3. Build Lean project (mathlib cache)
# -------------------------------------------
echo "[3/5] Building Lean project (this takes a while on first run)..."
cd lean
lake update
# Try to fetch cached oleans to avoid full rebuild
lake exe cache get 2>/dev/null || true
lake build
cd ..
echo "  Lean project built."

# -------------------------------------------
# 4. Pre-download model weights
# -------------------------------------------
echo "[4/5] Downloading DeepSeek-Prover model weights..."
# HF_TOKEN must be set if models are gated
python3 -c "
from huggingface_hub import snapshot_download
import os
token = os.environ.get('HF_TOKEN')
for model in ['deepseek-ai/DeepSeek-Prover-V1.5-RL', 'deepseek-ai/DeepSeek-Prover-V1.5']:
    print(f'  Downloading {model}...')
    snapshot_download(model, token=token)
    print(f'  Done: {model}')
"

# -------------------------------------------
# 5. Done — print run instructions
# -------------------------------------------
echo ""
echo "=== Setup Complete ==="
echo ""
echo "To start vLLM (RL model):"
echo "  python -m vllm.entrypoints.openai.api_server \\"
echo "    --model deepseek-ai/DeepSeek-Prover-V1.5-RL \\"
echo "    --tensor-parallel-size 1 \\"
echo "    --max-model-len 2048 \\"
echo "    --gpu-memory-utilization 0.9 &"
echo ""
echo "To start vLLM (BASE model):"
echo "  python -m vllm.entrypoints.openai.api_server \\"
echo "    --model deepseek-ai/DeepSeek-Prover-V1.5 \\"
echo "    --tensor-parallel-size 1 \\"
echo "    --max-model-len 2048 \\"
echo "    --gpu-memory-utilization 0.9 &"
echo ""
echo "To run all experiments (dry run first):"
echo "  bash scripts/run_all_experiments.sh --dry-run --provider openai_compat"
echo ""
echo "To run for real:"
echo "  bash scripts/run_all_experiments.sh --provider openai_compat"
echo ""
echo "Note: Exp 1+3 use the RL model, Exp 2 uses the BASE model."
echo "You'll need to restart vLLM with the other model between experiment groups."
echo ""
echo "To run RL experiments only (Exp 1 + 3), then BASE (Exp 2):"
echo "  # Start RL model, run Exp 1 + 3 manually, kill vLLM, start BASE model, run Exp 2"
echo ""
echo "Done at: $(date)"
