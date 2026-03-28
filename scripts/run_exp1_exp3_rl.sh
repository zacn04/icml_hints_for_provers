#!/usr/bin/env bash
# Exp 1 (extended budget) + Exp 3 (diversity ablation) — RL model only.
# Requires vLLM serving deepseek-ai/DeepSeek-Prover-V1.5-RL.
#
# Usage:
#   bash scripts/run_exp1_exp3_rl.sh [--dry-run] [--provider openai_compat] ...
set -euo pipefail
source "$(dirname "$0")/_experiment_common.sh"

print_header "Exp 1 + 3: RL Model (DeepSeek-Prover-V1.5-RL)"

# -----------------------------------------------
# Experiment 1: Extended Budget
# A-RL: sample (i.i.d.), B-RL: structured/skeleton
# -----------------------------------------------
for K in 16 32 64 128; do
    run_cmd "Exp1: A-RL sample pass@${K}" \
        python3 azure_job/run.py \
            --benchmark "$BENCHMARK" --model "$MODEL_RL" \
            --baseline sample --k "$K" --timeout "$TIMEOUT" --seed "$SEED" \
            --provider "$PROVIDER" $BASE_URL_FLAG \
            --condition "A-RL" --output-root "$OUTPUT_ROOT"

    run_cmd "Exp1: B-RL structured/skeleton pass@${K}" \
        python3 azure_job/run.py \
            --benchmark "$BENCHMARK" --model "$MODEL_RL" \
            --baseline structured --perturbation skeleton --k "$K" --timeout "$TIMEOUT" --seed "$SEED" \
            --provider "$PROVIDER" $BASE_URL_FLAG \
            --condition "B-RL" --output-root "$OUTPUT_ROOT"
done

# -----------------------------------------------
# Experiment 3: Diversity Ablation (k=16)
# C1: paraphrase, C2: comment
# -----------------------------------------------
run_cmd "Exp3: C1 structured/paraphrase pass@16" \
    python3 azure_job/run.py \
        --benchmark "$BENCHMARK" --model "$MODEL_RL" \
        --baseline structured --perturbation paraphrase --k 16 --timeout "$TIMEOUT" --seed "$SEED" \
        --provider "$PROVIDER" $BASE_URL_FLAG \
        --condition "C1" --output-root "$OUTPUT_ROOT"

run_cmd "Exp3: C2 structured/comment pass@16" \
    python3 azure_job/run.py \
        --benchmark "$BENCHMARK" --model "$MODEL_RL" \
        --baseline structured --perturbation comment --k 16 --timeout "$TIMEOUT" --seed "$SEED" \
        --provider "$PROVIDER" $BASE_URL_FLAG \
        --condition "C2" --output-root "$OUTPUT_ROOT"

echo ""
echo "=== Exp 1 + 3 complete. ==="
echo "You can now kill vLLM and switch to the BASE model for Exp 2:"
echo "  kill %1"
echo "  bash scripts/run_exp2_base.sh --provider $PROVIDER"
