#!/usr/bin/env bash
# Exp 1 (extended budget) + Exp 3 (diversity ablation) — RL model, 8-way sharded.
# Requires vLLM serving deepseek-ai/DeepSeek-Prover-V1.5-RL.
set -euo pipefail

SHARDS=8
MODEL="deepseek-ai/DeepSeek-Prover-V1.5-RL"
PROVIDER="${1:-openai_compat}"

echo "============================================"
echo "  Exp 1 + 3: RL Model (sharded x${SHARDS})"
echo "  Provider: $PROVIDER"
echo "  Started: $(date)"
echo "============================================"

run() {
    local cond="$1" base="$2" perturb="$3" k="$4"
    echo ""
    echo ">>> $cond $base/$perturb pass@${k} — $(date)"
    bash scripts/run_sharded.sh \
        --model "$MODEL" --baseline "$base" --perturbation "$perturb" \
        --k "$k" --condition "$cond" --shards "$SHARDS" --provider "$PROVIDER"
}

# Exp 1: Extended budget
for K in 16 32 64; do
    run "A-RL" "sample"     "skeleton" "$K"
    run "B-RL" "structured" "skeleton" "$K"
done

# Exp 3: Diversity ablation (k=16 only)
run "C1" "structured" "paraphrase" 16
run "C2" "structured" "comment"    16

echo ""
echo "============================================"
echo "  Exp 1 + 3 complete at $(date)"
echo "  Switch to BASE model for Exp 2:"
echo "    pkill -f vllm"
echo "    # start vLLM with DeepSeek-Prover-V1.5"
echo "    bash scripts/run_exp2_sharded.sh"
echo "============================================"
