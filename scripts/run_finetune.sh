#!/bin/bash
# =============================================================================
# IDS Symbol Renderer — Qwen3-32B QLoRA Fine-tune with MLX  (v5)
# Requirements: Apple Silicon Mac (36GB RAM), Python 3.10+
# 所要時間: M3 Max 36GB で 4〜8 時間
#
# v5 変更点:
#   - Qwen3-14B → Qwen3-32B に移行
#   - <構造>トークンに重なり率・まとまり度メトリクスを追加（prepare_finetune v5）
#   - --num-layers 16 → 8（32B はレイヤー数が多いためメモリ節約）
#   - fuse後に自動で4bit量子化（推論用）
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BASE_MODEL_DIR="$PROJECT_DIR/models/Qwen3-32B"
EXTENDED_DIR="$PROJECT_DIR/models/Qwen3-32B-extended"
QUANTIZED_DIR="$PROJECT_DIR/models/Qwen3-32B-extended-4bit"
ADAPTER_DIR="$PROJECT_DIR/models/qwen3-32b-ids-finetuned"
FUSED_DIR="$PROJECT_DIR/models/qwen3-32b-ids-fused"
FUSED_4BIT_DIR="$PROJECT_DIR/models/qwen3-32b-ids-fused-4bit"
FINETUNE_DIR="$PROJECT_DIR/finetune_data"

PYTHON=/Users/andotakahiro/radical-energy-model/venv/bin/python3

echo "============================================"
echo "  IDS Symbol Renderer — Fine-tuning v5"
echo "  (Qwen3-32B + QLoRA + overlap metrics)"
echo "============================================"
echo "  Base model:     $BASE_MODEL_DIR"
echo "  Extended model: $EXTENDED_DIR"
echo "  Quantized (4bit):$QUANTIZED_DIR"
echo "  Fused (bf16):   $FUSED_DIR"
echo "  Serving (4bit): $FUSED_4BIT_DIR"
echo ""

# ── Step 1: mlx-lm の確認 ──────────────────────────────────────────────────
echo "[1/7] Checking mlx-lm..."
$PYTHON -m pip install mlx-lm --quiet
$PYTHON -c "import mlx_lm; print('  mlx-lm OK:', mlx_lm.__version__)"

# ── Step 2: ベースモデルの確認 ──────────────────────────────────────────────
echo ""
echo "[2/7] Checking base model..."
if [ ! -f "$BASE_MODEL_DIR/config.json" ]; then
  echo "  Downloading Qwen3-32B (初回のみ、約65GB)..."
  $PYTHON -m pip install huggingface_hub hf_transfer --quiet
  HF_HUB_ENABLE_HF_TRANSFER=1 $PYTHON -c "
from huggingface_hub import snapshot_download
snapshot_download(repo_id='Qwen/Qwen3-32B', local_dir='$BASE_MODEL_DIR', local_dir_use_symlinks=False)
"
else
  echo "  Already present: $BASE_MODEL_DIR"
fi

# ── Step 3: トークナイザー拡張 ─────────────────────────────────────────────
echo ""
echo "[3/7] Extending tokenizer with special tokens..."
if [ -f "$EXTENDED_DIR/config.json" ] && [ -f "$EXTENDED_DIR/tokenizer.json" ] && [ -f "$EXTENDED_DIR/model.safetensors.index.json" ]; then
  echo "  Already extended: $EXTENDED_DIR"
  echo "  (削除して再生成するには: rm -rf $EXTENDED_DIR)"
else
  # 中途半端なディレクトリを削除してから再実行
  rm -rf "$EXTENDED_DIR"
  $PYTHON "$SCRIPT_DIR/extend_tokenizer.py"
  echo "  Tokenizer extension complete."
fi

# ── Step 4: 学習データ生成 ──────────────────────────────────────────────────
echo ""
echo "[4/7] Preparing training data (v5: CoT + overlap + cohesion)..."
$PYTHON "$SCRIPT_DIR/prepare_finetune.py"
TRAIN_COUNT=$(wc -l < "$FINETUNE_DIR/train.jsonl")
VALID_COUNT=$(wc -l < "$FINETUNE_DIR/valid.jsonl")
echo "  train: $TRAIN_COUNT 件  valid: $VALID_COUNT 件"

# ── Step 5a: 4bit量子化（QLoRA用）────────────────────────────────────────────
echo ""
echo "[5a/7] Quantizing extended model to 4-bit..."
if [ -f "$QUANTIZED_DIR/config.json" ]; then
  echo "  Already quantized: $QUANTIZED_DIR"
else
  $PYTHON -m mlx_lm.convert \
    --hf-path "$EXTENDED_DIR" \
    --mlx-path "$QUANTIZED_DIR" \
    --quantize \
    --q-bits 4
  # 特殊トークン付き tokenizer を量子化モデルにもコピー
  cp "$EXTENDED_DIR/tokenizer.json"        "$QUANTIZED_DIR/tokenizer.json"
  cp "$EXTENDED_DIR/tokenizer_config.json" "$QUANTIZED_DIR/tokenizer_config.json"
  echo "  Quantization complete: $QUANTIZED_DIR"
fi

# ── Step 5b: LoRA ファインチューニング（量子化ベース）────────────────────────
echo ""
echo "[5b/7] LoRA fine-tuning on 4-bit model (4〜8 時間)..."
echo ""

# MLX サーバーが動いていたら停止（メモリ確保のため）
pkill -f "mlx_lm server" 2>/dev/null && echo "  Stopped MLX server." || true
sleep 2

mkdir -p "$ADAPTER_DIR"

ITERS=$(wc -l < "$FINETUNE_DIR/train.jsonl" | tr -d ' ')
echo "  iters: $ITERS"

$PYTHON -m mlx_lm.lora \
  --model "$QUANTIZED_DIR" \
  --train \
  --data "$FINETUNE_DIR" \
  --fine-tune-type lora \
  --num-layers 8 \
  --config "$SCRIPT_DIR/lora_config.yaml" \
  --batch-size 1 \
  --iters "$ITERS" \
  --learning-rate 2e-4 \
  --steps-per-report 10 \
  --steps-per-eval 100 \
  --val-batches 10 \
  --max-seq-length 2048 \
  --grad-checkpoint \
  --adapter-path "$ADAPTER_DIR" \
  --save-every 200

echo ""
echo "  Fine-tuning complete."

# ── Step 6: 重みのフュージョン ───────────────────────────────────────────────
echo ""
echo "[6/7] Fusing weights..."

if [ -d "$FUSED_DIR" ]; then
  echo "  Removing old fused model..."
  rm -rf "$FUSED_DIR"
fi

mkdir -p "$FUSED_DIR"

$PYTHON -m mlx_lm.fuse \
  --model "$QUANTIZED_DIR" \
  --adapter-path "$ADAPTER_DIR" \
  --save-path "$FUSED_DIR" \
  --dequantize

# 特殊トークン付き tokenizer で上書き
cp "$EXTENDED_DIR/tokenizer.json"        "$FUSED_DIR/tokenizer.json"
cp "$EXTENDED_DIR/tokenizer_config.json" "$FUSED_DIR/tokenizer_config.json"
echo "  Fused model saved (bf16): $FUSED_DIR"

# ── Step 7: 推論用 4bit 量子化 ──────────────────────────────────────────────
echo ""
echo "[7/7] Quantizing fused model to 4-bit for serving..."

if [ -d "$FUSED_4BIT_DIR" ]; then
  echo "  Removing old 4-bit model..."
  rm -rf "$FUSED_4BIT_DIR"
fi

$PYTHON -m mlx_lm.convert \
  --hf-path "$FUSED_DIR" \
  --mlx-path "$FUSED_4BIT_DIR" \
  --quantize \
  --q-bits 4

cp "$EXTENDED_DIR/tokenizer.json"        "$FUSED_4BIT_DIR/tokenizer.json"
cp "$EXTENDED_DIR/tokenizer_config.json" "$FUSED_4BIT_DIR/tokenizer_config.json"
echo "  4-bit serving model saved: $FUSED_4BIT_DIR"

echo ""
echo "============================================"
echo "  Fine-tuning pipeline v5 complete!"
echo ""
echo "  start_mlx_server.sh の MODEL を"
echo "  $FUSED_4BIT_DIR"
echo "  に変更してから再起動してください。"
echo "============================================"
