#!/usr/bin/env bash
# Exp 2 (base vs RL) — BASE model, 8-way sharded.
# Requires vLLM serving deepseek-ai/DeepSeek-Prover-V1.5.
set -euo pipefail

SHARDS=8
MODEL="deepseek-ai/DeepSeek-Prover-V1.5"
PROVIDER="${1:-openai_compat}"

echo "============================================"
echo "  Exp 2: BASE Model (sharded x${SHARDS})"
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

for K in 16 32 64; do
    run "A-BASE" "sample"     "skeleton" "$K"
    run "B-BASE" "structured" "skeleton" "$K"
done

echo ""
echo "============================================"
echo "  Exp 2 complete at $(date)"
echo "  All experiments done! Download outputs/"
echo "============================================"
