#!/bin/bash
# データファイルをiCloudに自動バックアップ
# cron で毎時実行される（setup_cron.sh で設定）

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/ids-symbol-backup"
DATE=$(date +%Y-%m-%d)

mkdir -p "$BACKUP_DIR"

# 最新版を常に上書き（常時最新版を保持）
for f in results.jsonl ai_results.jsonl hybrid_results.jsonl scores.json trash.jsonl; do
  if [ -f "$PROJECT_DIR/$f" ]; then
    cp "$PROJECT_DIR/$f" "$BACKUP_DIR/$f"
  fi
done

# 日次スナップショット（その日の最後の状態を保存）
SNAP_DIR="$BACKUP_DIR/snapshots/$DATE"
mkdir -p "$SNAP_DIR"
for f in results.jsonl ai_results.jsonl hybrid_results.jsonl scores.json; do
  if [ -f "$PROJECT_DIR/$f" ]; then
    cp "$PROJECT_DIR/$f" "$SNAP_DIR/$f"
  fi
done

echo "[$(date '+%H:%M:%S')] backup done → $BACKUP_DIR"
