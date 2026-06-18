#!/usr/bin/env bash
# Shared argument parsing and helpers for experiment scripts.
# Source this, don't run it directly.

DRY_RUN=false
BENCHMARK="benchmarks/minif2f.jsonl"
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

print_header() {
    echo "============================================"
    echo "  $1"
    echo "============================================"
    echo "  Benchmark:  $BENCHMARK"
    echo "  Provider:   $PROVIDER"
    echo "  Timeout:    ${TIMEOUT}s"
    echo "  Seed:       $SEED"
    echo "  Output:     $OUTPUT_ROOT"
    echo "  Dry run:    $DRY_RUN"
    echo ""
}
