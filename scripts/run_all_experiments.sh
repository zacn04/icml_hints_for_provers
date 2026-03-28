#!/usr/bin/env bash
# run_all_experiments.sh — Launch all experiment conditions for the revision.
#
# Usage:
#   bash scripts/run_all_experiments.sh [--dry-run] [--benchmark PATH] [--provider PROVIDER] [--base-url URL]
#
# Defaults:
#   benchmark: azure_job/benchmarks/minif2f.jsonl
#   provider:  openai_compat
#   base-url:  (reads from VLLM_BASE_URL env var)

set -euo pipefail

DRY_RUN=false
BENCHMARK="azure_job/benchmarks/minif2f.jsonl"
PROVIDER="openai_compat"
BASE_URL=""
TIMEOUT=120
SEED=1
OUTPUT_ROOT="outputs"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)    DRY_RUN=true; shift ;;
        --benchmark)  BENCHMARK="$2"; shift 2 ;;
        --provider)   PROVIDER="$2"; shift 2 ;;
        --base-url)   BASE_URL="$2"; shift 2 ;;
        --timeout)    TIMEOUT="$2"; shift 2 ;;
        --seed)       SEED="$2"; shift 2 ;;
        --output-root) OUTPUT_ROOT="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

MODEL_RL="deepseek-ai/DeepSeek-Prover-V1.5-RL"
MODEL_BASE="deepseek-ai/DeepSeek-Prover-V1.5"

BASE_URL_FLAG=""
if [[ -n "$BASE_URL" ]]; then
    BASE_URL_FLAG="--base-url $BASE_URL"
fi

run_cmd() {
    local desc="$1"; shift
    echo ""
    echo "=== $desc ==="
    echo "  $*"
    if [[ "$DRY_RUN" == "false" ]]; then
        "$@"
    fi
}

echo "============================================"
echo "  Structured Hints Revision - All Experiments"
echo "============================================"
echo "  Benchmark:  $BENCHMARK"
echo "  Provider:   $PROVIDER"
echo "  Timeout:    ${TIMEOUT}s"
echo "  Seed:       $SEED"
echo "  Output:     $OUTPUT_ROOT"
echo "  Dry run:    $DRY_RUN"
echo ""

# -----------------------------------------------
# Experiment 1: Extended Budget (RL model)
# A-RL: sample (no skeleton), B-RL: structured/skeleton
# -----------------------------------------------
for K in 16 32 64 128; do
    run_cmd "Exp1: A-RL sample pass@${K}" \
        python azure_job/run.py \
            --benchmark "$BENCHMARK" --model "$MODEL_RL" \
            --baseline sample --k "$K" --timeout "$TIMEOUT" --seed "$SEED" \
            --provider "$PROVIDER" $BASE_URL_FLAG \
            --condition "A-RL" --output-root "$OUTPUT_ROOT"

    run_cmd "Exp1: B-RL structured/skeleton pass@${K}" \
        python azure_job/run.py \
            --benchmark "$BENCHMARK" --model "$MODEL_RL" \
            --baseline structured --perturbation skeleton --k "$K" --timeout "$TIMEOUT" --seed "$SEED" \
            --provider "$PROVIDER" $BASE_URL_FLAG \
            --condition "B-RL" --output-root "$OUTPUT_ROOT"
done

# -----------------------------------------------
# Experiment 2: Base vs RL
# A-BASE: sample, B-BASE: structured/skeleton
# -----------------------------------------------
for K in 16 32 64; do
    run_cmd "Exp2: A-BASE sample pass@${K}" \
        python azure_job/run.py \
            --benchmark "$BENCHMARK" --model "$MODEL_BASE" \
            --baseline sample --k "$K" --timeout "$TIMEOUT" --seed "$SEED" \
            --provider "$PROVIDER" $BASE_URL_FLAG \
            --condition "A-BASE" --output-root "$OUTPUT_ROOT"

    run_cmd "Exp2: B-BASE structured/skeleton pass@${K}" \
        python azure_job/run.py \
            --benchmark "$BENCHMARK" --model "$MODEL_BASE" \
            --baseline structured --perturbation skeleton --k "$K" --timeout "$TIMEOUT" --seed "$SEED" \
            --provider "$PROVIDER" $BASE_URL_FLAG \
            --condition "B-BASE" --output-root "$OUTPUT_ROOT"
done

# -----------------------------------------------
# Experiment 3: Diversity Ablation (RL model, k=16)
# C1: paraphrase, C2: comment
# -----------------------------------------------
run_cmd "Exp3: C1 structured/paraphrase pass@16" \
    python azure_job/run.py \
        --benchmark "$BENCHMARK" --model "$MODEL_RL" \
        --baseline structured --perturbation paraphrase --k 16 --timeout "$TIMEOUT" --seed "$SEED" \
        --provider "$PROVIDER" $BASE_URL_FLAG \
        --condition "C1" --output-root "$OUTPUT_ROOT"

run_cmd "Exp3: C2 structured/comment pass@16" \
    python azure_job/run.py \
        --benchmark "$BENCHMARK" --model "$MODEL_RL" \
        --baseline structured --perturbation comment --k 16 --timeout "$TIMEOUT" --seed "$SEED" \
        --provider "$PROVIDER" $BASE_URL_FLAG \
        --condition "C2" --output-root "$OUTPUT_ROOT"

echo ""
echo "============================================"
echo "  All experiments completed (or printed)."
echo "============================================"
