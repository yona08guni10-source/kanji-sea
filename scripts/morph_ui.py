#!/usr/bin/env python3
"""
morph_ui.py — 漢字連鎖モーフィング（プログレッシブ品質向上）
============================================================
・テキスト入力 → 漢字ごとに分解 → 隣接ペアをモーフィングしてループ
・バックグラウンドで N_STEPS を段階的に増やし解像度を上げ続ける
・leap スライダーで記号の跳躍的変化を制御
・インターリーブ処理で複数漢字でも固まらない

Usage:
  python scripts/morph_ui.py
  → http://localhost:7863
"""
import base64, io, json, math, sys, threading, time, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import numpy as np
import torch
from PIL import Image

ROOT     = Path(__file__).parent.parent
CKPT     = ROOT / "models" / "kanji_sans" / "model_epoch1000.pt"
DATA_DIR = ROOT / "data"  / "noto_kanji_sans" / "kanji"
PORT     = 7863
SEED     = 42

sys.path.insert(0, str(ROOT / "scripts"))
from symbol_diffusion import SymbolUNet, load_char_image

DEVICE = ("mps"  if torch.backends.mps.is_available() else
          "cuda" if torch.cuda.is_available()         else "cpu")

print("モデル読み込み中…")
_state   = torch.load(CKPT, map_location=DEVICE, weights_only=True)
IMG_SIZE = _state.get("img_size", 64)
model    = SymbolUNet(img_size=IMG_SIZE, base_ch=_state.get("base_ch", 48)).to(DEVICE)
model.load_state_dict(_state["model"])
model.eval()
print(f"  epoch={_state.get('epoch')}  loss={_state.get('loss',0):.5f}")

DEFAULT_CHARS  = ["喜", "怒", "哀", "楽"]
FRAMES_PER_SEG = 24
OUT_SIZE       = 512
QUALITY_STEPS  = [2, 5, 15, 40]   # 細分化: 最初は超高速
MAX_TEMP       = 0.85
BUMP_EVERY     = 6    # N フレームごとに部分更新通知

# ── 共有状態 ──────────────────────────────────────────────────────────────────
_lock = threading.Lock()
_buf  = {
    "chars":   list(DEFAULT_CHARS),
    "segs":    [],
    "frames":  {},   # (si,fi) -> {"quality": int, "image": dataURL}
    "fq":      {},   # "si-fi" -> quality  (status 用サマリー)
    "version": 0,
    "qlevel":  -1,
    "total":   0,
    "leap":    0.0,
    "curve":   0.1,   # 端点滞留カーブ: 小=すぐ変化 / 大=長く滞在
}

def _init_segs(chars):
    n = len(chars)
    return [(chars[i], chars[(i+1) % n]) for i in range(n)]

_buf["segs"]  = _init_segs(DEFAULT_CHARS)
_buf["total"] = len(_buf["segs"]) * FRAMES_PER_SEG


# ── フレーム生成 ───────────────────────────────────────────────────────────────
def _make_frame_png(img_a, img_b, alpha, n_steps, pair_seed, leap, curve) -> str:
    ramp     = min(alpha, 1 - alpha) * 2
    eff_temp = (ramp ** curve) * MAX_TEMP if ramp > 1e-9 else 0.0
    t_start  = 1.0 - eff_temp
    dt       = 1.0 / n_steps

    # 指向性ノイズ: noise_a → noise_b (巻き戻し防止)
    torch.manual_seed(pair_seed)
    noise_a = torch.randn(1, 1, IMG_SIZE, IMG_SIZE, device=DEVICE)
    torch.manual_seed(pair_seed + 1)
    noise_b = torch.randn(1, 1, IMG_SIZE, IMG_SIZE, device=DEVICE)
    base_noise = (1 - alpha) * noise_a + alpha * noise_b

    # フレームごとの独立ノイズ (leap)
    fi_idx = int(round(alpha * (FRAMES_PER_SEG - 1)))
    torch.manual_seed(pair_seed + 100000 + fi_idx)
    frame_noise = torch.randn(1, 1, IMG_SIZE, IMG_SIZE, device=DEVICE)

    noise   = (1 - leap) * base_noise + leap * frame_noise
    x_blend = ((1 - alpha) * img_a + alpha * img_b).clamp(-1, 1)

    if eff_temp < 1e-6:
        z = x_blend.unsqueeze(0)
    else:
        start_step = int(t_start * n_steps)
        z = t_start * x_blend.unsqueeze(0) + eff_temp * noise
        with torch.no_grad():
            for step in range(start_step, n_steps):
                t_val = torch.full((1,), step * dt, device=DEVICE)
                z = z + model(z, t_val) * dt

    arr  = ((z.squeeze().cpu().numpy() + 1) * 127.5).clip(0, 255).astype(np.uint8)
    pil  = Image.fromarray(arr, "L")
    arr2 = np.array(pil.resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS))
    bw   = np.where(arr2 < 160, 0, 255).astype(np.uint8)
    pil2 = Image.fromarray(bw, "L")
    buf  = io.BytesIO()
    pil2.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ── バックグラウンド計算スレッド ───────────────────────────────────────────────
def _changed(chars, leap, curve):
    """chars / leap / curve が変わったか確認（ロック外から呼ぶな）"""
    return (_buf["chars"] != chars
            or abs(_buf["leap"]  - leap)  > 1e-9
            or abs(_buf["curve"] - curve) > 1e-9)

def _compute_loop():
    char_cache = {}

    while True:
        with _lock:
            chars  = list(_buf["chars"])
            segs   = list(_buf["segs"])
            qlevel = _buf["qlevel"]
            leap   = _buf["leap"]
            curve  = _buf["curve"]

        if not segs or len(chars) < 2:
            time.sleep(0.3)
            continue

        next_q = qlevel + 1
        if next_q >= len(QUALITY_STEPS):
            time.sleep(2.0)
            continue

        n_steps = QUALITY_STEPS[next_q]
        print(f"品質向上: lv={next_q}  N_STEPS={n_steps}  "
              f"chars={''.join(chars)}  leap={leap:.2f}  curve={curve:.2f}")

        # 使う文字をロード
        needed = set(c for seg in segs for c in seg)
        for ch in needed:
            if ch not in char_cache:
                img = load_char_image(ch, DATA_DIR, IMG_SIZE)
                char_cache[ch] = img.to(DEVICE) if img is not None else None

        # セグメントデータ準備
        seg_data = []
        for ca, cb in segs:
            if char_cache.get(ca) is None or char_cache.get(cb) is None:
                seg_data.append(None)
                continue
            pair_seed = (SEED ^ (ord(ca)*2654435761) ^ (ord(cb)*2246822519)) & 0xFFFFFFFF
            seg_data.append((char_cache[ca], char_cache[cb], pair_seed))

        aborted   = False
        done_cnt  = 0

        # ── インターリーブ処理 ──
        # fi (フレーム) を外側、si (セグメント) を内側に:
        # → 全セグメントの frame0 を先に計算してから frame1, frame2 ... へ
        # → 複数漢字でも均等に進む / 固まらない
        # alpha = fi / FRAMES_PER_SEG → 最終フレームは alpha<1
        # セグメント境界で同じ文字が2フレーム連続するのを防ぐ
        for fi in range(FRAMES_PER_SEG):
            for si, data in enumerate(seg_data):
                with _lock:
                    if _changed(chars, leap, curve):
                        aborted = True
                        break
                if data is None:
                    continue
                img_a, img_b, pair_seed = data
                alpha = fi / FRAMES_PER_SEG          # [0, (N-1)/N]
                png   = _make_frame_png(img_a, img_b, alpha, n_steps,
                                        pair_seed, leap, curve)
                with _lock:
                    if not _changed(chars, leap, curve):
                        _buf["frames"][(si, fi)] = {"quality": next_q, "image": png}
                        _buf["fq"][f"{si}-{fi}"] = next_q
                        done_cnt += 1
                        if done_cnt % BUMP_EVERY == 0:
                            _buf["version"] += 1
            if aborted:
                break

        if not aborted:
            with _lock:
                if not _changed(chars, leap, curve):
                    _buf["qlevel"]  = next_q
                    _buf["version"] += 1
                    print(f"  → 完了 lv={next_q}  version={_buf['version']}")


threading.Thread(target=_compute_loop, daemon=True).start()


# ── HTML ───────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>漢字モーフィング</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{background:#fff;color:#111;font-family:sans-serif;
     display:flex;flex-direction:column;align-items:center;
     min-height:100vh;padding:32px 16px;}
h1{font-size:13px;letter-spacing:4px;color:#aaa;font-weight:400;margin-bottom:28px;}
#display{width:480px;height:480px;border:1px solid #e0e0e0;
         display:flex;align-items:center;justify-content:center;
         background:#fff;position:relative;}
#display img{width:100%;height:100%;object-fit:contain;display:block;}
#placeholder{color:#ccc;font-size:13px;}
#controls{margin-top:24px;display:flex;flex-direction:column;gap:14px;width:480px;}
.row{display:flex;align-items:center;gap:12px;}
#textInput{flex:1;padding:10px 14px;border:1px solid #ccc;border-radius:3px;
           font-size:20px;letter-spacing:6px;outline:none;}
#textInput:focus{border-color:#888;}
#setBtn{padding:10px 18px;background:#111;color:#fff;border:none;
        border-radius:3px;cursor:pointer;font-size:13px;white-space:nowrap;}
#setBtn:hover{background:#333;}
.sl-row{display:flex;align-items:center;gap:10px;font-size:12px;color:#999;}
.sl-row input{flex:1;accent-color:#111;}
.sl-val{width:36px;text-align:right;color:#aaa;font-variant-numeric:tabular-nums;}
#qualityBar{display:flex;gap:4px;align-items:center;font-size:11px;color:#bbb;flex-wrap:wrap;}
.qd{width:14px;height:14px;border-radius:2px;background:#eee;transition:background 0.3s;}
.qd.done{background:#111;}
.qd.partial{background:#bbb;}
#info{font-size:11px;color:#ccc;text-align:center;margin-top:4px;min-height:16px;}
#chars-display{font-size:18px;letter-spacing:8px;color:#ccc;min-height:28px;text-align:center;}
</style>
</head>
<body>
<h1>漢字モーフィング</h1>
<div id="display"><div id="placeholder">計算中…</div></div>
<div id="controls">
  <div id="chars-display"></div>
  <div class="row">
    <input id="textInput" type="text" placeholder="赤外線" maxlength="20">
    <button id="setBtn" onclick="submitChars()">設定</button>
  </div>
  <div class="sl-row">
    <span>ループ時間</span>
    <input type="range" id="loopSlider" min="1" max="60" value="4" step="0.5"
           oninput="loopVal.textContent=(+this.value).toFixed(1)+'s';setLoopDuration(+this.value)">
    <span class="sl-val" id="loopVal">4.0s</span>
    <span id="fpsInfo" style="font-size:10px;color:#ddd;margin-left:4px;"></span>
  </div>
  <div class="sl-row">
    <span>跳躍</span>
    <input type="range" id="leapSlider" min="0" max="1" value="0" step="0.05"
           oninput="leapVal.textContent=(+this.value).toFixed(2);setParam('leap',+this.value)">
    <span class="sl-val" id="leapVal">0.00</span>
  </div>
  <div class="sl-row">
    <span>滞留</span>
    <input type="range" id="curveSlider" min="0.05" max="2.0" value="0.1" step="0.05"
           oninput="curveVal.textContent=(+this.value).toFixed(2);setParam('curve',+this.value)">
    <span class="sl-val" id="curveVal">0.10</span>
  </div>
  <div id="qualityBar"></div>
  <div id="info"></div>
</div>

<script>
// ── 状態 ──────────────────────────────────────────────────────────────────────
let frameCache   = {};  // "si-fi" -> {image, quality}
let version      = -1;
let nSegs        = 0;
let nFrames      = 0;
let curSeg       = 0;
let curFrame     = 0;
let fps          = 24;
let loopDuration = 4.0;   // 1ループあたりの秒数
let lastTime     = 0;
let animId       = null;
let playing      = false;
let lastImgSrc   = null;

function setLoopDuration(sec){
  loopDuration = sec;
  recalcFPS();
}

function recalcFPS(){
  if(nSegs > 0 && nFrames > 0){
    fps = (nSegs * nFrames) / loopDuration;
    const el = document.getElementById('fpsInfo');
    if(el) el.textContent = `(${fps.toFixed(1)} fps)`;
  }
}

// キャッシュを「古い」とマーク（画像は残す、quality=-1 で再フェッチ対象に）
function markStale(){
  for(const key of Object.keys(frameCache)){
    if(frameCache[key]) frameCache[key].quality = -1;
  }
  version = -1;
}

// ── アニメーションループ ───────────────────────────────────────────────────────
function startLoop(){
  if(animId) cancelAnimationFrame(animId);
  playing = true;
  lastTime = performance.now();
  loop();
}

function loop(){
  animId = requestAnimationFrame(loop);
  const now = performance.now();
  const dt  = now - lastTime;
  if(dt < 1000/fps) return;
  lastTime = now - (dt % (1000/fps));

  if(nSegs===0 || nFrames===0) return;
  const key    = `${curSeg}-${curFrame}`;
  const entry  = frameCache[key];
  // キャッシュミス時は直前フレームを維持（ブランクにしない）
  const imgSrc = entry ? entry.image : lastImgSrc;
  if(imgSrc){
    const el = document.getElementById('display');
    let img = el.querySelector('img');
    if(!img){
      el.innerHTML = '';
      img = document.createElement('img');
      el.appendChild(img);
    }
    if(img.src !== imgSrc) img.src = imgSrc;
    if(entry) lastImgSrc = entry.image;
  }
  curFrame++;
  if(curFrame >= nFrames){
    curFrame = 0;
    curSeg   = (curSeg + 1) % nSegs;
  }
}

// ── フレーム取得（スマート: キャッシュより新しいものだけ） ─────────────────────
async function fetchFrame(si, fi){
  try{
    const r = await fetch(`/api/frame?seg=${si}&frame=${fi}`);
    if(!r.ok) return;
    const d = await r.json();
    if(!d.image) return;
    const key = `${si}-${fi}`;
    if(!frameCache[key] || frameCache[key].quality < d.quality){
      frameCache[key] = {image: d.image, quality: d.quality};
    }
  }catch(e){}
}

async function fetchNeeded(fq){
  // fq: {"si-fi": quality, ...}
  const toFetch = [];
  for(const [key, q] of Object.entries(fq)){
    if(!frameCache[key] || frameCache[key].quality < q) toFetch.push(key);
  }
  if(toFetch.length === 0) return 0;

  // 並列フェッチ (並列数制限)
  const CONCURRENCY = 10;
  for(let i=0; i<toFetch.length; i+=CONCURRENCY){
    const batch = toFetch.slice(i, i+CONCURRENCY);
    await Promise.all(batch.map(k=>{
      const [si,fi] = k.split('-').map(Number);
      return fetchFrame(si, fi);
    }));
  }
  return toFetch.length;
}

// ── サーバーポーリング ─────────────────────────────────────────────────────────
async function pollStatus(){
  try{
    const r = await fetch('api/status');
    const d = await r.json();

    // ループを明示: 喜 → 怒 → 哀 → 楽 → 喜
    document.getElementById('chars-display').textContent =
      d.chars.length > 1 ? d.chars.join(' → ') + ' → ' + d.chars[0] : d.chars[0] || '';
    nSegs   = d.n_segs;
    nFrames = d.frames_per_seg;
    if(curSeg >= nSegs) curSeg = 0;
    recalcFPS();

    // 品質バー
    const qb = document.getElementById('qualityBar');
    if(d.quality_steps){
      qb.innerHTML = '<span>品質</span>' +
        d.quality_steps.map((s,i)=>{
          const cls = i<=d.qlevel ? 'done' : (i===d.qlevel+1 ? 'partial' : '');
          return `<div class="qd ${cls}" title="N_STEPS=${s}"></div>`;
        }).join('') +
        `<span style="margin-left:4px;">${
          d.qlevel>=0 ? 'lv'+(d.qlevel+1)+'/'+d.quality_steps.length : '計算中'
        }</span>`;
    }

    // version が変わった or fq に新しいフレームがある
    if(d.version !== version){
      version = d.version;
      const n = await fetchNeeded(d.fq || {});
      const total = Object.keys(frameCache).length;
      document.getElementById('info').textContent =
        n>0 ? `+${n}フレーム更新 (計${total}枚)` : `${total}枚キャッシュ済`;
      if(!playing && total>0) startLoop();
    }
  }catch(e){}
  setTimeout(pollStatus, 600);
}

// ── パラメータ設定（leap / curve 共通） ──────────────────────────────────────
async function setParam(key, v){
  markStale();
  document.getElementById('info').textContent = `再計算中 (${key}変更)…`;
  await fetch('api/set_params', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({[key]: v})
  });
}

// ── 文字設定 ──────────────────────────────────────────────────────────────────
async function submitChars(){
  const text = document.getElementById('textInput').value.trim();
  if(!text) return;
  markStale();  // キャッシュを消さず古いとマーク → 再生継続したまま新フレームで上書き
  curFrame = 0;
  document.getElementById('info').textContent = '計算開始…';
  const leap  = +document.getElementById('leapSlider').value;
  const curve = +document.getElementById('curveSlider').value;
  await fetch('api/set_chars', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({text, leap, curve})
  });
}

document.getElementById('textInput').addEventListener('keydown', e=>{
  if(e.key==='Enter') submitChars();
});

pollStatus();
</script>
</body>
</html>"""


# ── HTTP Handler ───────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = urlparse(self.path)

        if p.path in ("/", "/index.html"):
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        elif p.path == "/api/status":
            with _lock:
                self._json({
                    "chars":          list(_buf["chars"]),
                    "n_segs":         len(_buf["segs"]),
                    "frames_per_seg": FRAMES_PER_SEG,
                    "version":        _buf["version"],
                    "qlevel":         _buf["qlevel"],
                    "quality_steps":  QUALITY_STEPS,
                    "total_frames":   _buf["total"],
                    "leap":           _buf["leap"],
                    "curve":          _buf["curve"],
                    "fq":             dict(_buf["fq"]),   # "si-fi" -> quality
                })

        elif p.path == "/api/frame":
            qs = parse_qs(p.query)
            si = int(qs.get("seg",   ["0"])[0])
            fi = int(qs.get("frame", ["0"])[0])
            with _lock:
                entry = _buf["frames"].get((si, fi))
            if entry:
                self._json(entry)
            else:
                self._json({"quality": -1, "image": ""})

        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length)) if length else {}

        if self.path == "/api/set_chars":
            text = body.get("text", "")
            leap = float(body.get("leap", 0.0))

            valid = []
            for ch in text:
                if (DATA_DIR / f"{ord(ch):05X}.png").exists():
                    valid.append(ch)
            seen = set()
            valid = [c for c in valid if not (c in seen or seen.add(c))]

            if len(valid) < 2:
                self._json({"error": "漢字が2文字以上必要です", "valid": valid}, 400)
                return

            curve = float(body.get("curve", _buf["curve"]))
            segs  = _init_segs(valid)
            with _lock:
                _buf["chars"]   = valid
                _buf["segs"]    = segs
                _buf["frames"]  = {}
                _buf["fq"]      = {}
                _buf["qlevel"]  = -1
                _buf["version"] += 1
                _buf["total"]   = len(segs) * FRAMES_PER_SEG
                _buf["leap"]    = max(0.0, min(1.0, leap))
                _buf["curve"]   = max(0.05, min(3.0, curve))

            print(f"文字設定: {''.join(valid)}  ({len(segs)}seg)  "
                  f"leap={leap:.2f}  curve={curve:.2f}")
            self._json({"ok": True, "chars": valid})

        elif self.path == "/api/set_params":
            leap  = float(body.get("leap",  _buf["leap"]))
            curve = float(body.get("curve", _buf["curve"]))
            with _lock:
                _buf["leap"]    = max(0.0,  min(1.0, leap))
                _buf["curve"]   = max(0.05, min(3.0, curve))
                _buf["frames"]  = {}
                _buf["fq"]      = {}
                _buf["qlevel"]  = -1
                _buf["version"] += 1

            print(f"パラメータ更新: leap={leap:.2f}  curve={curve:.2f}")
            self._json({"ok": True, "leap": leap})

        else:
            self.send_response(404); self.end_headers()


# ── 起動 ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    server = ThreadingHTTPServer(("localhost", PORT), Handler)
    url    = f"http://localhost:{PORT}"
    print(f"\n起動: {url}")
    print("Ctrl+C で終了\n")
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n終了")
