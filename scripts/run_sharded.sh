#!/usr/bin/env bash
# run_sharded.sh — Run a single experiment condition with N parallel shards.
#
# Usage:
#   bash scripts/run_sharded.sh --model MODEL --baseline BASE --perturbation PERTURB \
#     --k K --condition COND --shards 8 [--provider openai_compat]

set -euo pipefail

BENCHMARK="azure_job/benchmarks/minif2f.jsonl"
PROVIDER="openai_compat"
BASE_URL=""
TIMEOUT=120
SEED=1
OUTPUT_ROOT="outputs"
NUM_SHARDS=8
MODEL=""
BASELINE=""
PERTURBATION="skeleton"
K=16
CONDITION=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model)        MODEL="$2"; shift 2 ;;
        --baseline)     BASELINE="$2"; shift 2 ;;
        --perturbation) PERTURBATION="$2"; shift 2 ;;
        --k)            K="$2"; shift 2 ;;
        --condition)    CONDITION="$2"; shift 2 ;;
        --shards)       NUM_SHARDS="$2"; shift 2 ;;
        --benchmark)    BENCHMARK="$2"; shift 2 ;;
        --provider)     PROVIDER="$2"; shift 2 ;;
        --base-url)     BASE_URL="$2"; shift 2 ;;
        --timeout)      TIMEOUT="$2"; shift 2 ;;
        --seed)         SEED="$2"; shift 2 ;;
        --output-root)  OUTPUT_ROOT="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

if [[ -z "$MODEL" || -z "$BASELINE" || -z "$CONDITION" ]]; then
    echo "Error: --model, --baseline, and --condition are required"
    exit 1
fi

BASE_URL_FLAG=""
if [[ -n "$BASE_URL" ]]; then
    BASE_URL_FLAG="--base-url $BASE_URL"
fi

echo "=== $CONDITION: $BASELINE/$PERTURBATION pass@${K} (${NUM_SHARDS} shards) ==="

PIDS=()
for SHARD in $(seq 0 $((NUM_SHARDS - 1))); do
    python3 azure_job/run.py \
        --benchmark "$BENCHMARK" --model "$MODEL" \
        --baseline "$BASELINE" --perturbation "$PERTURBATION" \
        --k "$K" --timeout "$TIMEOUT" --seed "$SEED" \
        --provider "$PROVIDER" $BASE_URL_FLAG \
        --condition "$CONDITION" --output-root "$OUTPUT_ROOT" \
        --shard "$SHARD" --num-shards "$NUM_SHARDS" \
        > "/tmp/shard_${CONDITION}_k${K}_${SHARD}.log" 2>&1 &
    PIDS+=($!)
done

echo "  Launched ${NUM_SHARDS} shards: PIDs=${PIDS[*]}"

# Wait for all shards
FAILED=0
for PID in "${PIDS[@]}"; do
    if ! wait "$PID"; then
        FAILED=$((FAILED + 1))
    fi
done

if [[ $FAILED -gt 0 ]]; then
    echo "  WARNING: $FAILED shard(s) failed"
else
    echo "  All shards completed successfully"
fi
