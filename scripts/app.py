#!/usr/bin/env python3
"""
app.py — エントリポイント
=========================
1. proxy_ui.py をすぐに起動（Renderのタイムアウト回避）
2. バックグラウンドでHFからDL・展開・各ツール起動
"""
import os, sys, subprocess, time, threading
from pathlib import Path

ROOT    = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
PYTHON  = sys.executable
HF_REPO = os.environ.get("HF_MODEL_REPO", "")

TOOLS = [
    # 軽量ツール（numpy+PIL のみ、PyTorch不要）
    (7865, "tsne_ui.py",       "漢字 t-SNE 探索"),
    # 重量ツール（PyTorch+モデル必要）→ RAM不足のため要有料プラン
    # (7864, "tree_ui.py",       "漢字樹形図"),
    # (7868, "symbol_ui.py",     "漢字モーフィング"),
    # (7863, "morph_ui.py",      "漢字連鎖モーフィング"),
    # (7861, "tetra_ui.py",      "正四面体 重力場"),
    # (7866, "projection_ui.py", "記号の海"),
]

def setup_and_launch():
    """モデル・画像DL → 各ツール起動（バックグラウンドで実行）"""
    # ── モデルDL ──────────────────────────────────────────────────────────────
    CKPT = ROOT / "models" / "kanji_sans" / "model_epoch1000.pt"
    if not CKPT.exists() and HF_REPO:
        print(f"  [DL] モデル: {HF_REPO}")
        CKPT.parent.mkdir(parents=True, exist_ok=True)
        from huggingface_hub import hf_hub_download
        import shutil
        path = hf_hub_download(repo_id=HF_REPO, filename="model_epoch1000.pt")
        shutil.copy(path, CKPT)
        print(f"  [DL] モデル完了: {CKPT}")
    elif CKPT.exists():
        print(f"  モデル: {CKPT} (ローカル)")

    # ── 漢字画像DL・展開 ───────────────────────────────────────────────────────
    KANJI_DIR = ROOT / "data" / "noto_kanji_sans" / "kanji"
    if not KANJI_DIR.exists() and HF_REPO:
        print(f"  [DL] 漢字画像: {HF_REPO}")
        from huggingface_hub import hf_hub_download
        import shutil, tarfile
        tar_path = hf_hub_download(repo_id=HF_REPO, filename="data/kanji_images.tar.gz", repo_type="model")
        KANJI_DIR.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=str(ROOT / "data"))
        print(f"  [DL] 画像完了: {len(list(KANJI_DIR.glob('*.png')))}枚")
    elif KANJI_DIR.exists():
        print(f"  漢字画像: {KANJI_DIR} (ローカル)")

    # ── 各ツール起動 ───────────────────────────────────────────────────────────
    print("\n  記号の海 — ツール起動中\n  " + "=" * 30)
    for port, script, name in TOOLS:
        subprocess.Popen(
            [PYTHON, str(SCRIPTS / script)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        print(f"  [{port}] {name}")
        time.sleep(0.3)
    print("  全ツール起動完了\n")

# ── バックグラウンドでDL・起動 ─────────────────────────────────────────────────
t = threading.Thread(target=setup_and_launch, daemon=True)
t.start()

# ── proxy をすぐに起動（RenderのPORT listenタイムアウト回避）──────────────────
os.environ["PROXY_PORT"] = os.environ.get("PORT", "7860")
print(f"  プロキシ起動: port {os.environ['PROXY_PORT']}")
exec(open(str(SCRIPTS / "proxy_ui.py")).read())
