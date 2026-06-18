#!/usr/bin/env bash
# Exp 2 (base vs RL) — BASE model only.
# Requires vLLM serving deepseek-ai/DeepSeek-Prover-V1.5.
#
# Usage:
#   bash scripts/run_exp2_base.sh [--dry-run] [--provider openai_compat] ...
set -euo pipefail
source "$(dirname "$0")/_experiment_common.sh"

print_header "Exp 2: BASE Model (DeepSeek-Prover-V1.5)"

# -----------------------------------------------
# Experiment 2: Base vs RL
# A-BASE: sample (i.i.d.), B-BASE: structured/skeleton
# -----------------------------------------------
for K in 16 32 64; do
    run_cmd "Exp2: A-BASE sample pass@${K}" \
        python3 run.py \
            --benchmark "$BENCHMARK" --model "$MODEL_BASE" \
            --baseline sample --k "$K" --timeout "$TIMEOUT" --seed "$SEED" \
            --provider "$PROVIDER" $BASE_URL_FLAG \
            --condition "A-BASE" --output-root "$OUTPUT_ROOT"

    run_cmd "Exp2: B-BASE structured/skeleton pass@${K}" \
        python3 run.py \
            --benchmark "$BENCHMARK" --model "$MODEL_BASE" \
            --baseline structured --perturbation skeleton --k "$K" --timeout "$TIMEOUT" --seed "$SEED" \
            --provider "$PROVIDER" $BASE_URL_FLAG \
            --condition "B-BASE" --output-root "$OUTPUT_ROOT"
done

echo ""
echo "=== Exp 2 complete. ==="
echo "All experiments done. Download outputs/ and terminate the pod."
