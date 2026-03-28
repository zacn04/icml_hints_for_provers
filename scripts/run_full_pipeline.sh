#!/usr/bin/env bash
# run_full_pipeline.sh — Run ALL experiments unattended.
# Exp 1+3 (RL model) → switch vLLM → Exp 2 (BASE model)
set -euo pipefail

export PATH=$HOME/.local/bin:$HOME/.elan/bin:$PATH
export VLLM_NO_USAGE_STATS=1

SHARDS=8
MODEL_RL="deepseek-ai/DeepSeek-Prover-V1.5-RL"
MODEL_BASE="deepseek-ai/DeepSeek-Prover-V1.5"
PROVIDER="openai_compat"

cd /home/ubuntu/autoform

start_vllm() {
    local model="$1"
    echo ">>> Starting vLLM with $model at $(date)"
    pkill -9 -f "vllm.entrypoints" 2>/dev/null || true
    sleep 3

    nohup python3 -m vllm.entrypoints.openai.api_server \
        --model "$model" \
        --tensor-parallel-size 1 \
        --max-model-len 2048 \
        --gpu-memory-utilization 0.9 \
        --enforce-eager \
        --trust-remote-code \
        > /tmp/vllm.log 2>&1 &

    for i in $(seq 1 120); do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo ">>> vLLM ready with $model"
            return 0
        fi
        sleep 5
    done
    echo ">>> FATAL: vLLM failed to start"
    tail -30 /tmp/vllm.log
    exit 1
}

run() {
    local cond="$1" base="$2" perturb="$3" k="$4"
    echo ""
    echo ">>> $cond $base/$perturb pass@${k} — $(date)"
    bash scripts/run_sharded.sh \
        --model "$5" --baseline "$base" --perturbation "$perturb" \
        --k "$k" --condition "$cond" --shards "$SHARDS" --provider "$PROVIDER"
}

echo "============================================"
echo "  FULL EXPERIMENT PIPELINE"
echo "  Started: $(date)"
echo "============================================"

# =============================================
# PHASE 1: RL model (Exp 1 + 3)
# =============================================
start_vllm "$MODEL_RL"

echo ""
echo "========== EXP 1: Extended Budget (RL) =========="
for K in 16 32 64; do
    run "A-RL" "sample"     "skeleton" "$K" "$MODEL_RL"
    run "B-RL" "structured" "skeleton" "$K" "$MODEL_RL"
done

echo ""
echo "========== EXP 3: Diversity Ablation =========="
run "C1" "structured" "paraphrase" 16 "$MODEL_RL"
run "C2" "structured" "comment"    16 "$MODEL_RL"

echo ""
echo ">>> Exp 1 + 3 complete at $(date)"

# =============================================
# PHASE 2: BASE model (Exp 2)
# =============================================
echo ""
echo "========== SWITCHING TO BASE MODEL =========="

# Download BASE model weights first
python3 -c "
from huggingface_hub import snapshot_download
import os
snapshot_download('$MODEL_BASE', token=os.environ.get('HF_TOKEN'))
print('BASE model downloaded')
"

start_vllm "$MODEL_BASE"

echo ""
echo "========== EXP 2: Base vs RL =========="
for K in 16 32 64; do
    run "A-BASE" "sample"     "skeleton" "$K" "$MODEL_BASE"
    run "B-BASE" "structured" "skeleton" "$K" "$MODEL_BASE"
done

echo ""
echo "============================================"
echo "  ALL EXPERIMENTS COMPLETE"
echo "  Finished: $(date)"
echo "============================================"

# Summary
echo ""
echo "=== RESULTS SUMMARY ==="
for f in outputs/*/events.jsonl; do
    if [[ -f "$f" ]]; then
        total=$(grep -c '"trial"' "$f" 2>/dev/null || echo 0)
        proved=$(grep -c '"proved": true' "$f" 2>/dev/null || echo 0)
        echo "  $f: $proved/$total proved"
    fi
done
