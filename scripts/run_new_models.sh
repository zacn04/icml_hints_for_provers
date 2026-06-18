#!/usr/bin/env bash
# Run A-RL (sample) and B-RL (skeleton) at k=16,32 for three new models.
# Designed for a single A100 pod — runs models sequentially, shards in parallel.
set -euo pipefail

# Make lean/lake visible (nohup shells don't source ~/.bashrc)
export PATH="$HOME/.elan/bin:$PATH"

BENCHMARK="benchmarks/minif2f.jsonl"
TIMEOUT=120
SEED=1
NUM_SHARDS=8
PROVIDER="openai_compat"
OUTPUT_ROOT="outputs_new"

MODELS=(
    "deepseek-ai/DeepSeek-Prover-V2-7B"
    "AI-MO/Kimina-Prover-Preview-Distill-7B"
)

# Reasoning provers need long budgets for their CoT proof plan
MAX_TOKENS=8192
MAX_MODEL_LEN=10240

run_sharded() {
    local MODEL=$1
    local BASELINE=$2
    local K=$3
    local PERTURBATION=${4:-skeleton}
    local CONDITION="${BASELINE}_${PERTURBATION}_k${K}"

    echo "=== Running $CONDITION on $(basename $MODEL) ==="

    pids=()
    for SHARD in $(seq 0 $((NUM_SHARDS - 1))); do
        python3 run.py \
            --benchmark "$BENCHMARK" \
            --model "$MODEL" \
            --baseline "$BASELINE" \
            --k "$K" \
            --timeout "$TIMEOUT" \
            --seed "$SEED" \
            --provider "$PROVIDER" \
            --perturbation "$PERTURBATION" \
            --condition "$CONDITION" \
            --shard "$SHARD" \
            --num-shards "$NUM_SHARDS" \
            --output-root "$OUTPUT_ROOT" \
            --max-tokens "$MAX_TOKENS" \
            > "/tmp/shard_${CONDITION}_$(basename $MODEL)_${SHARD}.log" 2>&1 &
        pids+=($!)
    done

    echo "  Waiting for ${#pids[@]} shards..."
    for pid in "${pids[@]}"; do
        wait "$pid" || echo "  WARNING: shard $pid failed"
    done
    echo "  Done: $CONDITION"
}

start_vllm() {
    local MODEL=$1
    echo ">>> Starting vLLM for $MODEL ..."

    # Kill any existing vLLM API server AND its engine-core workers.
    # The API server and engine core are separate processes; pkill on
    # "vllm.entrypoints" only gets the API server, leaving a zombie engine
    # core holding the GPU. Kill anything mentioning vllm, then reclaim the GPU.
    pkill -9 -f "vllm.entrypoints" 2>/dev/null || true
    pkill -9 -f "VLLM::EngineCore" 2>/dev/null || true
    pkill -9 -f "multiprocessing.resource_tracker" 2>/dev/null || true
    # As a last resort, kill anything still using GPU 0
    for pid in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null); do
        kill -9 "$pid" 2>/dev/null || true
    done
    sleep 5

    python3 -m vllm.entrypoints.openai.api_server \
        --model "$MODEL" \
        --tensor-parallel-size 1 \
        --max-model-len "$MAX_MODEL_LEN" \
        --gpu-memory-utilization 0.9 \
        --enforce-eager \
        --trust-remote-code \
        > /tmp/vllm_$(basename $MODEL).log 2>&1 &

    # Wait for vLLM to be ready (larger context models take longer to load)
    echo "  Waiting for vLLM to start..."
    for i in $(seq 1 300); do
        if curl -s http://localhost:8000/v1/models > /dev/null 2>&1; then
            echo "  vLLM ready after ${i}s"
            return 0
        fi
        sleep 1
    done
    echo "  ERROR: vLLM failed to start within 300s"
    cat /tmp/vllm_$(basename $MODEL).log | tail -20
    return 1
}

# ============================================================
# Main loop: for each model, start vLLM, run 4 conditions
# ============================================================

for MODEL in "${MODELS[@]}"; do
    echo ""
    echo "========================================"
    echo "MODEL: $MODEL"
    echo "========================================"

    start_vllm "$MODEL"

    # A (i.i.d. sample) at k=16, k=32
    run_sharded "$MODEL" "sample" 16
    run_sharded "$MODEL" "sample" 32

    # B (skeleton) at k=16, k=32
    run_sharded "$MODEL" "structured" 16
    run_sharded "$MODEL" "structured" 32

    echo ">>> Done with $MODEL, stopping vLLM..."
    pkill -9 -f "vllm.entrypoints" 2>/dev/null || true
    pkill -9 -f "VLLM::EngineCore" 2>/dev/null || true
    sleep 5
done

echo ""
echo "========================================="
echo "ALL DONE. Results in $OUTPUT_ROOT/"
echo "========================================="
