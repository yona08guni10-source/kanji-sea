#!/usr/bin/env python3
"""
app.py — HF Spaces エントリポイント
=====================================
起動時に HF Hub からモデルをダウンロードし、
全ツールをバックグラウンドで起動。
proxy_ui.py をポート 7860 でフォアグラウンド実行。
"""
import os, sys, subprocess, time
from pathlib import Path

ROOT    = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
PYTHON  = sys.executable

# ── モデルをHF Hubからダウンロード ────────────────────────────────────────────
CKPT = ROOT / "models" / "kanji_sans" / "model_epoch1000.pt"
HF_REPO = os.environ.get("HF_MODEL_REPO", "")  # 例: andotakahiro/kanji-diffusion

if not CKPT.exists() and HF_REPO:
    print(f"  モデルをダウンロード中: {HF_REPO}")
    CKPT.parent.mkdir(parents=True, exist_ok=True)
    from huggingface_hub import hf_hub_download
    path = hf_hub_download(repo_id=HF_REPO, filename="model_epoch1000.pt")
    import shutil
    shutil.copy(path, CKPT)
    print(f"  完了: {CKPT}")
elif CKPT.exists():
    print(f"  モデル: {CKPT} (ローカル)")
else:
    print("  警告: モデルが見つかりません。HF_MODEL_REPO 環境変数を設定してください。")

# ── 漢字画像をHF Hubからダウンロード・展開 ────────────────────────────────────
KANJI_DIR = ROOT / "data" / "noto_kanji_sans" / "kanji"
if not KANJI_DIR.exists() and HF_REPO:
    print(f"  漢字画像をダウンロード中: {HF_REPO}")
    from huggingface_hub import hf_hub_download
    import shutil, tarfile
    tar_path = hf_hub_download(repo_id=HF_REPO, filename="data/kanji_images.tar.gz", repo_type="model")
    KANJI_DIR.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(path=str(ROOT / "data"))
    print(f"  完了: {len(list(KANJI_DIR.glob('*.png')))}枚")
elif KANJI_DIR.exists():
    print(f"  漢字画像: {KANJI_DIR} (ローカル, {len(list(KANJI_DIR.glob('*.png')))}枚)")

# ── 各ツールをバックグラウンド起動 ───────────────────────────────────────────
TOOLS = [
    (7865, "tsne_ui.py",       "漢字 t-SNE 探索"),
    (7864, "tree_ui.py",       "漢字樹形図"),
    (7868, "symbol_ui.py",     "漢字モーフィング"),
    (7863, "morph_ui.py",      "漢字連鎖モーフィング"),
    (7861, "tetra_ui.py",      "正四面体 重力場"),
    (7866, "projection_ui.py", "記号の海"),
]

print("\n  記号の海 — 起動中\n  " + "=" * 30)

for port, script, name in TOOLS:
    subprocess.Popen(
        [PYTHON, str(SCRIPTS / script)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    print(f"  [{port}] {name}")
    time.sleep(0.3)

print()

# ── proxy_ui.py を公開ポートで起動（HF Spaces: 7860, Render: $PORT）────────
os.environ["PROXY_PORT"] = os.environ.get("PORT", "7860")
exec(open(str(SCRIPTS / "proxy_ui.py")).read())
