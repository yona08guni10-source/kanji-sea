#!/usr/bin/env python3
"""
symbol_ui.py — 漢字モーフィング動画生成 UI
============================================
モデル : models/kanji_sans/model_epoch1000.pt  (SymbolUNet 64×64 Gothic)
全フレームを potrace ベクター化してから ffmpeg でエンコードする。
Usage:
  python scripts/symbol_ui.py
"""

import io
import sys
import math
import tempfile
import subprocess
from pathlib import Path

import cairosvg
import gradio as gr
import numpy as np
import torch
from PIL import Image

ROOT     = Path(__file__).parent.parent
CKPT     = ROOT / "models" / "kanji_sans" / "model_epoch1000.pt"
DATA_DIR = ROOT / "data"  / "noto_kanji_sans" / "kanji"

sys.path.insert(0, str(ROOT / "scripts"))
from symbol_diffusion import SymbolUNet, load_char_image

DEVICE = (
    "mps"  if torch.backends.mps.is_available() else
    "cuda" if torch.cuda.is_available()         else
    "cpu"
)

# ── モデル読み込み ─────────────────────────────────────────────────────────────
print("モデル読み込み中… (SymbolUNet Gothic 64×64)")
state    = torch.load(CKPT, map_location=DEVICE, weights_only=True)
IMG_SIZE = state.get("img_size", 64)
model    = SymbolUNet(img_size=IMG_SIZE, base_ch=state.get("base_ch", 48)).to(DEVICE)
model.load_state_dict(state["model"])
model.eval()
print(f"  epoch={state.get('epoch')}  loss={state.get('loss', 0):.5f}")

OUT_PX    = 512
THRESHOLD = 160
N_STEPS   = 10
SEED      = 42

_tmpdir = Path(tempfile.mkdtemp(prefix="symbol_ui_"))


# ── 画像処理 ──────────────────────────────────────────────────────────────────

def tensor_to_pil(t: torch.Tensor) -> Image.Image:
    arr = ((t.squeeze(0).cpu().numpy() + 1.0) * 127.5).clip(0, 255).astype(np.uint8)
    return Image.fromarray(arr, "L")


def vectorize(pil_img: Image.Image) -> Image.Image:
    pbm = _tmpdir / "f.pbm"
    svg = _tmpdir / "f.svg"
    arr = np.array(pil_img.resize((OUT_PX, OUT_PX), Image.LANCZOS))
    bw  = np.where(arr < THRESHOLD, 0, 255).astype(np.uint8)
    Image.fromarray(bw, "L").save(str(pbm))
    subprocess.run(
        ["potrace", "-s", "-W", f"{OUT_PX}pt", "-H", f"{OUT_PX}pt",
         "-o", str(svg), str(pbm)],
        check=True, capture_output=True,
    )
    png = cairosvg.svg2png(
        url=str(svg), background_color="white",
        output_width=OUT_PX, output_height=OUT_PX,
    )
    return Image.open(io.BytesIO(png)).convert("RGB")


# ── 動画生成 ──────────────────────────────────────────────────────────────────

def generate_video(
    char_a:         str,
    char_b:         str,
    fps:            int,
    duration_sec:   float,
    expressiveness: float,   # max_temp（中間フレームの最大変形量）
    leap:           float,   # フレームごとのノイズ独立度
    curve:          float,   # ランプのべき乗: <1=すぐ変化 / 1=線形 / >1=端点に長く滞在
    progress=gr.Progress(track_tqdm=False),
):
    char_a = char_a.strip()
    char_b = char_b.strip()

    if len(char_a) != 1 or len(char_b) != 1:
        raise gr.Error("1文字ずつ入力してください")

    img_a = load_char_image(char_a, DATA_DIR, IMG_SIZE)
    img_b = load_char_image(char_b, DATA_DIR, IMG_SIZE)
    if img_a is None:
        raise gr.Error(f"「{char_a}」が学習データに見つかりません")
    if img_b is None:
        raise gr.Error(f"「{char_b}」が学習データに見つかりません")

    img_a = img_a.to(DEVICE)
    img_b = img_b.to(DEVICE)

    n_frames = max(int(fps * duration_sec), 1)
    dt_flow  = 1.0 / N_STEPS

    # seedを文字の組み合わせから生成 → 同じ中間記号を経由しなくなる
    pair_seed = SEED ^ (ord(char_a[0]) * 2654435761) ^ (ord(char_b[0]) * 2246822519)
    pair_seed &= 0xFFFFFFFF
    # char_a側・char_b側それぞれのノイズ → alphaで合成することで巻き戻しを防ぐ
    torch.manual_seed(pair_seed)
    noise_a = torch.randn(1, 1, IMG_SIZE, IMG_SIZE, device=DEVICE)
    torch.manual_seed(pair_seed + 1)
    noise_b = torch.randn(1, 1, IMG_SIZE, IMG_SIZE, device=DEVICE)

    frame_dir = _tmpdir / "frames"
    frame_dir.mkdir(exist_ok=True)
    for f in frame_dir.glob("*.png"):
        f.unlink()

    progress(0, desc=f"生成中… 0/{n_frames}")

    with torch.no_grad():
        for i in range(n_frames):
            alpha = i / max(n_frames - 1, 1)

            # エントロピー温度（グリッドと同じ方式）:
            #   w = [1-alpha, alpha]  → 2文字の重み
            #   entropy / log(2)  → 0(端点) 〜 1(中間) に正規化
            # curve スライダーでランプの形を制御
            # ramp^curve: curve<1=早期から変化 / curve=1=線形 / curve>1=端点に長く滞在
            ramp     = min(alpha, 1 - alpha) * 2           # 三角波 [0,1]
            eff_temp = (ramp ** curve) * min(expressiveness, 0.85)
            t_start    = 1.0 - eff_temp
            start_step = int(t_start * N_STEPS)

            # ノイズをalphaで補間: char_a方向→char_b方向へ一方向に流れる
            frame_noise = torch.randn(1, 1, IMG_SIZE, IMG_SIZE, device=DEVICE)
            base_noise  = (1 - alpha) * noise_a + alpha * noise_b
            noise = (1 - leap) * base_noise + leap * frame_noise

            x_blend = (1 - alpha) * img_a + alpha * img_b
            z = t_start * x_blend.unsqueeze(0) + eff_temp * noise

            for step in range(start_step, N_STEPS):
                t_val = torch.full((1,), step * dt_flow, device=DEVICE)
                z = z + model(z, t_val) * dt_flow

            raw = tensor_to_pil(z.clamp(-1, 1).squeeze(0))
            vec = vectorize(raw)
            vec.save(str(frame_dir / f"frame_{i:04d}.png"))

            progress((i + 1) / n_frames, desc=f"生成中… {i+1}/{n_frames}")

    # ffmpeg エンコード
    out_path = str(_tmpdir / "output.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(frame_dir / "frame_%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        out_path,
    ], check=True, capture_output=True)

    return out_path


# ── Gradio UI ─────────────────────────────────────────────────────────────────

with gr.Blocks(title="漢字モーフィング") as demo:
    gr.Markdown("# 漢字モーフィング\nGothic 64×64 + potrace ベクター化")

    with gr.Row():
        char_a = gr.Textbox(label="開始", value="道", max_lines=1, scale=1)
        char_b = gr.Textbox(label="終了", value="器", max_lines=1, scale=1)

    with gr.Row():
        fps          = gr.Slider(1,  60,   value=24,  step=1,   label="FPS")
        duration_sec = gr.Slider(1,  30,   value=5,   step=0.5, label="動画時間（秒）")

    with gr.Row():
        expressiveness = gr.Slider(0.0, 1.5, value=1.0, step=0.05,
                                   label="temperature  0=直線補間 / 1=グリッドと同じ / 1.5=過変形")
        leap           = gr.Slider(0.0, 1.0, value=0.0, step=0.05,
                                   label="記号の跳躍的変化  0=滑らか / 1=フレームごとに独立")

    curve = gr.Slider(0.1, 3.0, value=0.4, step=0.1,
                      label="curve  小=すぐ変化が始まる / 1=線形 / 大=端点に長く滞在")

    btn = gr.Button("生成", variant="primary")
    video = gr.Video(label="出力", height=OUT_PX)

    btn.click(
        fn=generate_video,
        inputs=[char_a, char_b, fps, duration_sec, expressiveness, leap, curve],
        outputs=video,
    )

if __name__ == "__main__":
    demo.launch(server_port=7868, share=False)
