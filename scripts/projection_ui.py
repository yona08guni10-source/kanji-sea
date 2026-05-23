#!/usr/bin/env python3
"""
projection_ui.py — 記号の海 v4（多拠点モーフィング・左上始まり）
=============================================================
Port: 7866

動作:
  1. 鑑賞者が複数の漢字を入力（Enter キーでオーバーレイ）
  2. AI が順に漢字をモーフィング（ウェイポイント→ウェイポイント→…を循環）
  3. 各フレームを左上から縦に描画し、列が埋まったら右へ、画面が埋まったら左スクロール
  4. 生成中にランダムな分岐点で別の漢字へのモーフを派生
"""
import base64, io, json, math, queue, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
from PIL import Image
import torch

PORT     = 7866
ROOT     = Path(__file__).parent.parent
CKPT     = ROOT / "models" / "kanji_sans" / "model_epoch1000.pt"
DATA_DIR = ROOT / "data" / "noto_kanji_sans" / "kanji"

sys.path.insert(0, str(ROOT / "scripts"))
from symbol_diffusion import SymbolUNet, load_char_image

DEVICE = (
    "mps"  if torch.backends.mps.is_available() else
    "cuda" if torch.cuda.is_available()         else
    "cpu"
)

# ── モデル ────────────────────────────────────────────────────────────────────
print("モデル読み込み中…")
state    = torch.load(CKPT, map_location=DEVICE, weights_only=True)
IMG_SIZE = state.get("img_size", 64)
model    = SymbolUNet(img_size=IMG_SIZE, base_ch=state.get("base_ch", 48)).to(DEVICE)
model.load_state_dict(state["model"])
model.eval()
print(f"  epoch={state.get('epoch')}  loss={state.get('loss',0):.5f}")

# ── KNN データ ────────────────────────────────────────────────────────────────
print("漢字データ読み込み中…")
_TSNE_DIR = ROOT / "data" / "tsne"
_chars    = np.load(str(_TSNE_DIR / "kanji_chars.npy"), allow_pickle=True)
_X50      = np.load(str(_TSNE_DIR / "kanji_x50.npy")).astype(np.float32)
_char2idx = {c: i for i, c in enumerate(_chars)}
print(f"  {len(_chars)}字 完了")

# ── 定数 ──────────────────────────────────────────────────────────────────────
N_MORPH_FRAMES = 16
N_STEPS        = 10
CURVE          = 0.4
MAX_TEMP       = 0.78
MAX_QUEUE      = 12
BRANCH_PROB    = 0.55

# ── SSE クライアント ──────────────────────────────────────────────────────────
_sse_clients = []
_sse_lock    = threading.Lock()

def _broadcast(obj: dict):
    msg = ("data: " + json.dumps(obj, ensure_ascii=False) + "\n\n").encode()
    with _sse_lock:
        dead = []
        for q in _sse_clients:
            try:
                q.put_nowait(msg)
            except Exception:
                dead.append(q)
        for d in dead:
            _sse_clients.remove(d)


# ── KNN ──────────────────────────────────────────────────────────────────────
_KNN_CACHE: dict = {}

def _sorted_nn(char: str) -> list:
    if char in _KNN_CACHE:
        return _KNN_CACHE[char]
    if char not in _char2idx:
        return []
    idx   = _char2idx[char]
    diffs = _X50 - _X50[idx]
    dists = (diffs * diffs).sum(axis=1)
    dists[idx] = 1e18
    order = np.argsort(dists).tolist()
    _KNN_CACHE[char] = order
    return order


def _pick_neighbor(char: str, rng: np.random.Generator,
                   k: int = 30, escape_prob: float = 0.0) -> str:
    nn = _sorted_nn(char)
    if not nn:
        return char
    if escape_prob > 0 and rng.random() < escape_prob:
        far = nn[k: min(500, len(nn))]
        if far:
            return str(_chars[rng.choice(far)])
    local = nn[:k]
    weights = np.array([1.0 / (i + 1) for i in range(len(local))], dtype=np.float32)
    weights /= weights.sum()
    return str(_chars[rng.choice(local, p=weights)])


# ── ソース画像 ────────────────────────────────────────────────────────────────
def _source_b64(char: str):
    path = DATA_DIR / f"{ord(char):05X}.png"
    if not path.exists():
        return None
    return base64.b64encode(path.read_bytes()).decode()


# ── ウェイポイント（複数漢字） ────────────────────────────────────────────────
_waypoints: list = []
_wp_lock = threading.Lock()


def _next_waypoint(char_b: str, rng: np.random.Generator) -> str:
    """ウェイポイント列に従い次の文字を返す。char_b がウェイポイント外なら近傍選択。"""
    with _wp_lock:
        wp = list(_waypoints)
    if not wp:
        return _pick_neighbor(char_b, rng, k=25, escape_prob=0.30)
    if char_b in wp:
        idx = wp.index(char_b)
        return wp[(idx + 1) % len(wp)]
    # 分岐先からはランダムに続ける
    return _pick_neighbor(char_b, rng, k=25, escape_prob=0.30)


# ── ジョブキュー ──────────────────────────────────────────────────────────────
_job_queue  = queue.Queue(maxsize=MAX_QUEUE + 4)
_queue_lock = threading.Lock()

def _make_job(img_a: torch.Tensor, char_a: str, char_b: str) -> dict:
    return {'img_a': img_a.cpu(), 'char_a': char_a, 'char_b': char_b}


def reset_queue(chars_str: str):
    """キューを空にして、入力漢字列からウェイポイントチェーンを再スタート。"""
    global _waypoints
    chars = [c for c in chars_str if not c.isspace()]
    if not chars:
        return

    while not _job_queue.empty():
        try:
            _job_queue.get_nowait()
        except queue.Empty:
            break

    with _wp_lock:
        _waypoints = chars

    first_char = chars[0]
    source_b64 = _source_b64(first_char) or ''
    _broadcast({"type": "char", "char": ''.join(chars)})
    if source_b64:
        _broadcast({"type": "source", "img": source_b64})

    rng = np.random.default_rng(abs(hash(first_char)) % (2**32))

    if len(chars) > 1:
        target = chars[1]
    else:
        target = _pick_neighbor(first_char, rng, k=20, escape_prob=0.4)

    img_a = load_char_image(first_char, DATA_DIR, IMG_SIZE)
    if img_a is None:
        img_a = torch.zeros(1, IMG_SIZE, IMG_SIZE)
    _job_queue.put(_make_job(img_a, first_char, target))


# ── モーフ生成ループ ──────────────────────────────────────────────────────────
def _generator_loop():
    rng = np.random.default_rng(0)
    dt  = 1.0 / N_STEPS

    while True:
        try:
            job = _job_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        char_a = job['char_a']
        char_b = job['char_b']
        img_a  = job['img_a']

        img_b = load_char_image(char_b, DATA_DIR, IMG_SIZE)
        if img_b is None:
            char_b = _pick_neighbor(char_a, rng)
            img_b  = load_char_image(char_b, DATA_DIR, IMG_SIZE)
            if img_b is None:
                continue

        img_a_dev = img_a.to(DEVICE)
        img_b_dev = img_b.to(DEVICE)

        _broadcast({"type": "newline"})

        pair_seed = (abs(hash(char_a)) ^ (abs(hash(char_b)) * 2654435761)) & 0xFFFFFFFF
        torch.manual_seed(pair_seed)
        noise_a = torch.randn(1, 1, IMG_SIZE, IMG_SIZE, device=DEVICE)
        torch.manual_seed(pair_seed + 1)
        noise_b = torch.randn(1, 1, IMG_SIZE, IMG_SIZE, device=DEVICE)

        do_branch    = rng.random() < BRANCH_PROB
        branch_frame = int(rng.integers(N_MORPH_FRAMES // 4, 3 * N_MORPH_FRAMES // 4))
        branch_added = False

        with torch.no_grad():
            for i in range(N_MORPH_FRAMES):
                alpha = i / max(N_MORPH_FRAMES - 1, 1)

                ramp     = min(alpha, 1.0 - alpha) * 2.0
                eff_temp = (ramp ** CURVE) * MAX_TEMP
                t_start  = 1.0 - eff_temp

                noise   = (1.0 - alpha) * noise_a + alpha * noise_b
                x_blend = (1.0 - alpha) * img_a_dev + alpha * img_b_dev
                z       = t_start * x_blend.unsqueeze(0) + eff_temp * noise

                for step in range(int(t_start * N_STEPS), N_STEPS):
                    t_val = torch.full((1,), step * dt, device=DEVICE)
                    z     = z + model(z, t_val) * dt

                z = z.clamp(-1, 1)

                arr = ((z.squeeze().cpu().numpy() + 1.0) * 127.5).clip(0, 255).astype(np.uint8)
                buf = io.BytesIO()
                Image.fromarray(arr, "L").save(buf, format="PNG", optimize=False)
                b64 = base64.b64encode(buf.getvalue()).decode()
                _broadcast({"type": "frame", "img": b64})

                if do_branch and i == branch_frame and not branch_added:
                    branch_char = _pick_neighbor(char_b, rng, k=40, escape_prob=0.50)
                    try:
                        _job_queue.put_nowait(
                            _make_job(z.squeeze(0).cpu(), char_b, branch_char)
                        )
                        branch_added = True
                    except queue.Full:
                        pass

        # 次ジョブ: ウェイポイントに従い循環
        next_char = _next_waypoint(char_b, rng)
        try:
            _job_queue.put_nowait(_make_job(img_b.cpu(), char_b, next_char))
        except queue.Full:
            try:
                _job_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                _job_queue.put_nowait(_make_job(img_b.cpu(), char_b, next_char))
            except queue.Full:
                pass


threading.Thread(target=_generator_loop, daemon=True).start()
reset_queue("門")


# ── HTML ──────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>記号の海</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body {
  width: 100%; height: 100%;
  background: #f5f5f5;
  overflow: hidden;
  font-family: 'Hiragino Sans', 'Noto Sans CJK JP', sans-serif;
}
canvas {
  display: block;
  position: fixed;
  top: 0; left: 0;
}

/* 選択中の漢字（左下） */
#cur-char {
  position: fixed;
  bottom: 20px; left: 24px;
  font-size: 10px;
  letter-spacing: 5px;
  color: rgba(0,0,0,0.15);
  pointer-events: none;
  z-index: 10;
}

/* ── 入力オーバーレイ ────────────────── */
#overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(245,245,245,0.88);
  backdrop-filter: blur(8px);
  z-index: 100;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 22px;
}
#overlay.on { display: flex; }

#ov-label {
  font-size: 10px;
  letter-spacing: 8px;
  color: rgba(0,0,0,0.25);
}
#ov-prompt {
  display: flex;
  align-items: baseline;
  gap: 8px;
  border-bottom: 1px solid rgba(0,0,0,0.15);
  padding-bottom: 4px;
}
#ov-caret {
  font-size: 20px;
  color: rgba(0,0,0,0.25);
  font-family: monospace;
  line-height: 1;
}
#char-input {
  width: 300px;
  font-size: 48px;
  line-height: 1;
  background: transparent;
  border: none;
  color: #111;
  outline: none;
  text-align: left;
  caret-color: rgba(0,0,0,0.4);
  font-family: 'Hiragino Sans', 'Noto Sans CJK JP', sans-serif;
  letter-spacing: 4px;
}
#ov-hint {
  font-size: 9px;
  letter-spacing: 3px;
  color: rgba(0,0,0,0.12);
}
</style>
</head>
<body>
<canvas id="c"></canvas>
<div id="cur-char">門</div>

<div id="overlay">
  <div id="ov-label">記号を選ぶ（複数可）</div>
  <div id="ov-prompt">
    <span id="ov-caret">›</span>
    <input id="char-input" type="text" maxlength="20"
           autocomplete="off" spellcheck="false">
  </div>
  <div id="ov-hint">Enter で確定 / Esc でキャンセル</div>
</div>

<script>
// ── Canvas ───────────────────────────────────────────────────────────────────
const canvas = document.getElementById('c');
const ctx    = canvas.getContext('2d');
let W, H, dpr;

const CELL = 74;
const GAP  = 2;
const STEP = CELL + GAP;

// ── リングバッファ（左上始まり・左スクロール）────────────────────────────────
//
// Phase 1: 左→右に列を埋めていく（画面が埋まるまで）
//   writeSlot = 現在書き込み中のスロット（= 画面列インデックスと同じ）
//   sx = writeSlot * STEP
//
// Phase 2: 画面が埋まったらリングバッファに移行、左スクロール
//   writeSlot は最右列に対応
//   c=COLS-1: writeSlot, c=COLS-2: writeSlot-1, ..., c=0: writeSlot+1 (mod COLS)
//   sx = c * STEP + slideOffset  (slideOffset: STEP→0 でスライドアニメ)
//
let COLS, ROWS;
let slots     = [];   // slots[slotIdx][row] = ImageBitmap|null
let writeSlot = 0;
let headRow   = 0;
let totalCols = 0;    // 完了した列数（Phase判定用）
let phase     = 1;    // 1=左から埋まる中, 2=リングバッファ

let slideOffset = 0;
let targetSlide = 0;

function initGrid() {
  COLS = Math.floor(W / STEP);
  ROWS = Math.floor(H / STEP);
  slots = Array.from({length: COLS}, () => new Array(ROWS).fill(null));
  writeSlot = 0; headRow = 0; totalCols = 0; phase = 1;
  slideOffset = 0; targetSlide = 0;
}

function fillAll(bmp) {
  for (let c = 0; c < COLS; c++)
    for (let r = 0; r < ROWS; r++)
      slots[c][r] = bmp;
  // Phase 1 にリセット → 新コンテンツが左上から流れ始める
  writeSlot = 0; headRow = 0; totalCols = 0; phase = 1;
  slideOffset = 0; targetSlide = 0;
}

function addFrame(bmp) {
  slots[writeSlot][headRow] = bmp;
  headRow++;
  if (headRow >= ROWS) {
    headRow = 0;
    if (phase === 1) {
      totalCols++;
      if (totalCols < COLS) {
        writeSlot = totalCols;  // 次の列へ（Phase 1: 線形）
      } else {
        // 画面が埋まった → Phase 2 へ移行
        phase = 2;
        writeSlot = (writeSlot + 1) % COLS;  // = 0
        slideOffset = STEP;
        targetSlide = 0;
      }
    } else {
      writeSlot = (writeSlot + 1) % COLS;
      slideOffset = STEP;
      targetSlide = 0;
    }
  }
}

// ── リサイズ ──────────────────────────────────────────────────────────────────
function resize() {
  dpr = window.devicePixelRatio || 1;
  W   = window.innerWidth;
  H   = window.innerHeight;
  canvas.width  = W * dpr;
  canvas.height = H * dpr;
  canvas.style.width  = W + 'px';
  canvas.style.height = H + 'px';
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  initGrid();
}
window.addEventListener('resize', resize);
resize();

// ── レンダリングループ ────────────────────────────────────────────────────────
function render() {
  slideOffset += (targetSlide - slideOffset) * 0.11;
  if (Math.abs(targetSlide - slideOffset) < 0.3) slideOffset = targetSlide;

  ctx.fillStyle = '#f5f5f5';
  ctx.fillRect(0, 0, W, H);

  if (phase === 1) {
    // 全スロットを表示（fillAll後は全列にソース画像あり、新コンテンツで上書き中）
    for (let c = 0; c < COLS; c++) {
      const sx = c * STEP;
      if (sx > W) break;
      for (let r = 0; r < ROWS; r++) {
        const bmp = slots[c][r];
        if (bmp) ctx.drawImage(bmp, sx, r * STEP, CELL, CELL);
      }
    }
  } else {
    // Phase 2: リングバッファ・左アンカー
    // c=COLS-1 (最右) → writeSlot
    // c=COLS-2        → (writeSlot-1+COLS)%COLS
    // c=0   (最左)   → (writeSlot+1)%COLS
    // slotIdx(c) = (writeSlot - (COLS-1-c) + COLS*100) % COLS
    //            = (writeSlot + 1 + c) % COLS
    for (let c = 0; c <= COLS; c++) {   // COLS+1 でスライドイン列も描画
      const sx = c * STEP + slideOffset;
      if (sx + CELL < 0 || sx > W) continue;
      const slotIdx = (writeSlot + 1 + c) % COLS;
      for (let r = 0; r < ROWS; r++) {
        const bmp = slots[slotIdx][r];
        if (bmp) ctx.drawImage(bmp, sx, r * STEP, CELL, CELL);
      }
    }
  }

  requestAnimationFrame(render);
}
render();

// ── フレーム読み込み ──────────────────────────────────────────────────────────
async function loadBitmap(b64) {
  const img = new Image();
  img.src = 'data:image/png;base64,' + b64;
  await new Promise(r => { img.onload = r; img.onerror = r; });
  const oc  = new OffscreenCanvas(CELL, CELL);
  const ocx = oc.getContext('2d');
  ocx.fillStyle = '#f5f5f5';
  ocx.fillRect(0, 0, CELL, CELL);
  ocx.drawImage(img, 0, 0, CELL, CELL);
  return createImageBitmap(oc);
}

// ── SSE ──────────────────────────────────────────────────────────────────────
function connectSSE() {
  const es = new EventSource('/api/stream');
  es.onmessage = async e => {
    let d;
    try { d = JSON.parse(e.data); } catch { return; }

    if (d.type === 'char') {
      document.getElementById('cur-char').textContent = d.char;

    } else if (d.type === 'source') {
      const bmp = await loadBitmap(d.img);
      fillAll(bmp);

    } else if (d.type === 'frame') {
      const bmp = await loadBitmap(d.img);
      addFrame(bmp);

    }
    // newline は無視（列管理は addFrame 内で自動）
  };
  es.onerror = () => { es.close(); setTimeout(connectSSE, 2000); };
}
connectSSE();

// ── 入力オーバーレイ ──────────────────────────────────────────────────────────
const overlay   = document.getElementById('overlay');
const charInput = document.getElementById('char-input');

function openOverlay() {
  overlay.classList.add('on');
  charInput.value = '';
  setTimeout(() => charInput.focus(), 60);
}
function closeOverlay() { overlay.classList.remove('on'); }

async function submitChar() {
  const raw = charInput.value.trim();
  closeOverlay();
  if (!raw) return;
  await fetch('api/select', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chars: raw })
  });
}

document.addEventListener('keydown', e => {
  if (overlay.classList.contains('on')) {
    if (e.key === 'Enter')  submitChar();
    if (e.key === 'Escape') closeOverlay();
  } else {
    if (e.key === 'Enter') openOverlay();
  }
});
</script>
</body>
</html>
"""


# ── HTTP ──────────────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass

    def do_GET(self):
        path = urlparse(self.path).path

        if path == '/':
            body = HTML.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif path == '/api/stream':
            q = queue.Queue(maxsize=800)
            with _sse_lock:
                _sse_clients.append(q)

            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()

            try:
                while True:
                    try:
                        msg = q.get(timeout=20)
                        self.wfile.write(msg)
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b': ping\n\n')
                        self.wfile.flush()
            except Exception:
                pass
            finally:
                with _sse_lock:
                    if q in _sse_clients:
                        _sse_clients.remove(q)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/select':
            length = int(self.headers.get('Content-Length', 0))
            body   = self.rfile.read(length)
            try:
                data = json.loads(body)
                chars = data.get('chars', '').strip()
                if chars:
                    threading.Thread(target=reset_queue, args=(chars,), daemon=True).start()
            except Exception as e:
                print(f"[select] {e}")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == '__main__':
    server = ThreadingHTTPServer(('', PORT), Handler)
    print(f"\n  記号の海  →  http://localhost:{PORT}\n")
    server.serve_forever()
