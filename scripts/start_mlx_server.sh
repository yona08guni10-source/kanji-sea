#!/bin/bash
# mlx-lm inference server for qwen3-14b-ids
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MODEL="$PROJECT_DIR/models/qwen3-14b-ids-fused-4bit"

echo "Starting mlx-lm server on port 11435..."
echo "Model: $MODEL"

/Users/andotakahiro/radical-energy-model/venv/bin/python3 -m mlx_lm server \
  --model "$MODEL" \
  --port 11435 \
  --temp 0.6 \
  --top-p 0.95 \
  --top-k 40 \
  --prompt-cache-size 0 \
  --chat-template-args '{"enable_thinking": true}'
