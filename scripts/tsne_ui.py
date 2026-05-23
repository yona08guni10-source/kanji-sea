#!/usr/bin/env python3
"""
tsne_ui.py — 漢字 t-SNE 探索 UI
==================================
Port: 7865
事前に kanji_tsne_bn.npy / kanji_chars.npy / kanji_x50.npy が
/tmp/ に生成済みであること。
"""
import base64, io, json, sys, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import numpy as np
from PIL import Image

PORT     = 7865
ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "data" / "noto_kanji_sans" / "kanji"
TSNE_DIR = ROOT / "data" / "tsne"

# ── データ読み込み ─────────────────────────────────────────────────────────────
print("データ読み込み中…")
_X2       = np.load(str(TSNE_DIR / "kanji_tsne_bn.npy")).astype(np.float32)
_chars    = np.load(str(TSNE_DIR / "kanji_chars.npy"), allow_pickle=True)
_radicals = np.load(str(TSNE_DIR / "kanji_radicals.npy")).astype(np.int32)
_strokes  = np.load(str(TSNE_DIR / "kanji_strokes.npy")).astype(np.int32)
_X50      = np.load(str(TSNE_DIR / "kanji_x50.npy")).astype(np.float32)

N = len(_chars)
_xmin, _xmax = float(_X2[:,0].min()), float(_X2[:,0].max())
_ymin, _ymax = float(_X2[:,1].min()), float(_X2[:,1].max())
_nx = ((_X2[:,0] - _xmin) / (_xmax - _xmin))
_ny = ((_X2[:,1] - _ymin) / (_ymax - _ymin))
_char2idx = {c: i for i, c in enumerate(_chars)}
print(f"  {N}字 完了")


# ── KNN（ボトルネック PCA-50 空間）────────────────────────────────────────────
def knn(idx: int, k: int = 16):
    diffs = _X50 - _X50[idx]
    dists = (diffs * diffs).sum(axis=1)
    dists[idx] = 1e18
    nn = np.argpartition(dists, k)[:k]
    nn = nn[np.argsort(dists[nn])]
    return [(int(i), float(np.sqrt(dists[i]))) for i in nn]


# ── 画像 ─────────────────────────────────────────────────────────────────────
def char_b64(char: str) -> str:
    path = DATA_DIR / f"{ord(char):05X}.png"
    if not path.exists():
        return ""
    buf = io.BytesIO()
    Image.open(path).convert("L").resize((128, 128), Image.LANCZOS).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# ── HTML ──────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>漢字 t-SNE 探索</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{background:#f5f5f5;color:#222;font-family:'Hiragino Sans','Helvetica Neue',sans-serif;
     display:flex;height:100vh;overflow:hidden;}

/* ── サイドバー ──────────────────────── */
#sidebar{width:300px;flex-shrink:0;display:flex;flex-direction:column;
         background:#fff;border-right:1px solid #e0e0e0;z-index:10;}

#search-area{padding:14px;border-bottom:1px solid #e8e8e8;}
#search-area h1{font-size:10px;letter-spacing:5px;color:#aaa;font-weight:400;margin-bottom:12px;}
#search-row{display:flex;gap:8px;align-items:center;}
#searchInput{width:56px;font-size:30px;text-align:center;padding:4px 6px;
             background:#f8f8f8;border:1px solid #ddd;border-radius:4px;
             color:#111;outline:none;}
#searchInput:focus{border-color:#999;}
#searchBtn{flex:1;padding:8px;background:#f0f0f0;border:1px solid #ddd;
           border-radius:4px;color:#666;cursor:pointer;font-size:12px;}
#searchBtn:hover{background:#e4e4e4;color:#333;}
#status{font-size:11px;color:#bbb;margin-top:8px;min-height:15px;}

#sel-area{padding:14px;border-bottom:1px solid #e8e8e8;}
#sel-title{font-size:10px;color:#bbb;letter-spacing:2px;margin-bottom:10px;}
#sel-body{display:flex;gap:12px;align-items:center;}
#sel-img{width:76px;height:76px;border:1px solid #e0e0e0;border-radius:4px;
         background:#fafafa;object-fit:contain;flex-shrink:0;}
#sel-meta{font-size:11px;color:#999;line-height:1.9;}
#sel-char-big{font-size:38px;color:#111;display:block;line-height:1;}

#rad-area{padding:14px;border-bottom:1px solid #e8e8e8;max-height:180px;overflow-y:auto;}
#rad-title{font-size:10px;color:#bbb;letter-spacing:2px;margin-bottom:8px;}
#rad-chars{display:flex;flex-wrap:wrap;gap:4px;}
.rad-ch{font-size:18px;color:#444;cursor:pointer;padding:2px 4px;border-radius:3px;
        line-height:1.3;transition:background .1s;}
.rad-ch:hover{background:#f0f0f0;color:#000;}

#nb-area{flex:1;overflow-y:auto;padding:14px;}
#nb-title{font-size:10px;color:#bbb;letter-spacing:2px;margin-bottom:10px;}
#nb-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;}
.nb-item{cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:3px;}
.nb-item img{width:100%;aspect-ratio:1;border:1px solid #e0e0e0;border-radius:3px;
             background:#fafafa;display:block;transition:border-color .12s;}
.nb-item:hover img{border-color:#999;}
.nb-char{font-size:13px;color:#555;}
.nb-dist{font-size:9px;color:#ccc;}

/* ── マップ ──────────────────────────── */
#map-area{flex:1;position:relative;overflow:hidden;background:#fff;}
canvas{position:absolute;top:0;left:0;cursor:crosshair;}
canvas.panning{cursor:grabbing;}

#legend{position:absolute;bottom:12px;right:12px;background:rgba(255,255,255,.92);
        border:1px solid #e0e0e0;border-radius:4px;padding:9px 11px;
        font-size:10px;color:#888;backdrop-filter:blur(4px);}
.leg-row{display:flex;align-items:center;gap:7px;margin-bottom:3px;}
.leg-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}

#tooltip{position:absolute;background:#fff;border:1px solid #ddd;
         border-radius:3px;padding:3px 8px;font-size:13px;color:#333;
         pointer-events:none;display:none;z-index:20;white-space:nowrap;
         box-shadow:0 2px 8px rgba(0,0,0,.08);}

#hint{position:absolute;top:12px;left:12px;font-size:11px;color:#ccc;
      pointer-events:none;}
</style>
</head>
<body>

<div id="sidebar">
  <div id="search-area">
    <h1>漢字 t-SNE 探索</h1>
    <div id="search-row">
      <input id="searchInput" type="text" maxlength="1" placeholder="漢">
      <button id="searchBtn" onclick="doSearch()">検索</button>
    </div>
    <div id="status">読み込み中…</div>
  </div>

  <div id="sel-area">
    <div id="sel-title">選択中</div>
    <div id="sel-body"><span style="color:#bbb;font-size:12px;">漢字を検索またはクリック</span></div>
  </div>

  <div id="rad-area" style="display:none;">
    <div id="rad-title">同じ部首の漢字</div>
    <div id="rad-chars"></div>
  </div>

  <div id="nb-area">
    <div id="nb-title">近隣の漢字（モデル内部空間）</div>
    <div id="nb-grid"></div>
  </div>
</div>

<div id="map-area">
  <canvas id="c"></canvas>
  <div id="tooltip"></div>
  <div id="legend"></div>
  <div id="hint">ホイール: ズーム　ドラッグ: 移動　クリック: 選択</div>
</div>

<script>
// ── 定数 ─────────────────────────────────────────────────────────────────────
const PAD = 30;
const GROUPS = [
  {name:'門構え (門)', rad:169, color:'#cc2222'},
  {name:'木偏 (木)',   rad: 75, color:'#228822'},
  {name:'水偏 (氵)',   rad: 85, color:'#2255cc'},
  {name:'口偏 (口)',   rad: 30, color:'#cc7700'},
  {name:'人偏 (亻)',   rad:  9, color:'#882299'},
  {name:'手偏 (扌)',   rad: 64, color:'#007788'},
  {name:'心偏 (忄)',   rad: 61, color:'#cc3344'},
  {name:'金偏 (金)',   rad:167, color:'#887700'},
];
const RAD_COLOR = Object.fromEntries(GROUPS.map(g=>[g.rad, g.color]));

// ── 状態 ─────────────────────────────────────────────────────────────────────
let data = null, N = 0;
let scale = 1, panX = 0, panY = 0;
let selIdx = null, nbIdxs = [];
let groupIdxs = {}, bgIdxs = [];
let W, H, dpr = 1;

// ── Canvas ────────────────────────────────────────────────────────────────────
const canvas = document.getElementById('c');
const ctx    = canvas.getContext('2d');

// ── RAF バッチ描画 ────────────────────────────────────────────────────────────
let rafId = null;
function scheduleRender(){
  if(rafId) return;
  rafId = requestAnimationFrame(()=>{ rafId=null; render(); });
}

function resize(){
  dpr = window.devicePixelRatio || 1;
  const area = document.getElementById('map-area');
  W = area.clientWidth; H = area.clientHeight;
  canvas.width  = W * dpr;
  canvas.height = H * dpr;
  canvas.style.width  = W + 'px';
  canvas.style.height = H + 'px';
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  scheduleRender();
}

// ── 座標変換 ─────────────────────────────────────────────────────────────────
function toScreen(nx, ny){
  return [nx*(W-PAD*2)*scale + panX + PAD,
          ny*(H-PAD*2)*scale + panY + PAD];
}
function findNearest(sx, sy, maxPx=18){
  if(!data) return -1;
  const sw = (W-PAD*2)*scale, sh = (H-PAD*2)*scale;
  const nx_c = (sx-panX-PAD)/sw, ny_c = (sy-panY-PAD)/sh;
  let best=-1, bestD=maxPx*maxPx;
  for(let i=0;i<N;i++){
    const dsx=(data.nx[i]-nx_c)*sw, dsy=(data.ny[i]-ny_c)*sh;
    const d=dsx*dsx+dsy*dsy;
    if(d<bestD){bestD=d;best=i;}
  }
  return best;
}

// ── 描画 ─────────────────────────────────────────────────────────────────────
const TEXT_SCALE = 4;    // これ以上のzoomで文字表示
const DOT_SCALE  = 2;    // これ以上でドットを少し大きく

function render(){
  if(!data) return;
  ctx.clearRect(0,0,W,H);

  const showText = scale >= TEXT_SCALE;
  const fontSize = Math.max(10, Math.min(36, scale * 1.8));

  if(showText){
    // ── 文字モード: 全点を文字で描画（可視領域のみ）─────────────────────────
    ctx.font = `${fontSize}px "Hiragino Sans","Noto Sans CJK JP",sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    // まず背景点を薄い文字で
    ctx.fillStyle = 'rgba(160,160,160,0.7)';
    for(const i of bgIdxs){
      const [sx,sy]=toScreen(data.nx[i],data.ny[i]);
      if(sx<-fontSize||sx>W+fontSize||sy<-fontSize||sy>H+fontSize) continue;
      ctx.fillText(data.chars[i], sx, sy);
    }
    // グループ点をカラー文字で
    for(const g of GROUPS){
      ctx.fillStyle = g.color;
      for(const i of groupIdxs[g.rad]||[]){
        const [sx,sy]=toScreen(data.nx[i],data.ny[i]);
        if(sx<-fontSize||sx>W+fontSize||sy<-fontSize||sy>H+fontSize) continue;
        ctx.fillText(data.chars[i], sx, sy);
      }
    }

  } else {
    // ── ドットモード: グループ別バッチ描画（高速）────────────────────────────
    const r = scale >= DOT_SCALE ? 1.5 : 1;
    ctx.fillStyle='#cccccc';
    for(const i of bgIdxs){
      const [sx,sy]=toScreen(data.nx[i],data.ny[i]);
      if(sx<-4||sx>W+4||sy<-4||sy>H+4) continue;
      ctx.fillRect(sx-r,sy-r,r*2,r*2);
    }
    for(const g of GROUPS){
      ctx.fillStyle=g.color;
      for(const i of groupIdxs[g.rad]||[]){
        const [sx,sy]=toScreen(data.nx[i],data.ny[i]);
        if(sx<-4||sx>W+4||sy<-4||sy>H+4) continue;
        ctx.fillRect(sx-r,sy-r,r*2,r*2);
      }
    }
  }

  // 近隣ハイライト（黄リング）
  for(const i of nbIdxs){
    const [sx,sy]=toScreen(data.nx[i],data.ny[i]);
    if(showText){
      // 文字の背後に黄色背景
      ctx.fillStyle='rgba(255,200,50,0.25)';
      const hw=fontSize*0.6;
      ctx.fillRect(sx-hw,sy-hw,hw*2,hw*2);
      // 枠線
      ctx.strokeStyle='rgba(255,200,50,0.8)';
      ctx.lineWidth=1.5;
      ctx.strokeRect(sx-hw,sy-hw,hw*2,hw*2);
    } else {
      ctx.fillStyle='rgba(255,200,50,0.85)';
      ctx.beginPath(); ctx.arc(sx,sy,5,0,Math.PI*2); ctx.fill();
    }
  }

  // 選択ハイライト
  if(selIdx!==null){
    const [sx,sy]=toScreen(data.nx[selIdx],data.ny[selIdx]);
    // 十字線
    ctx.strokeStyle='rgba(0,0,0,0.12)';
    ctx.lineWidth=1; ctx.setLineDash([3,5]);
    ctx.beginPath(); ctx.moveTo(sx,0); ctx.lineTo(sx,H); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(0,sy); ctx.lineTo(W,sy); ctx.stroke();
    ctx.setLineDash([]);
    if(showText){
      // 文字モード: 白枠で囲む
      const hw=fontSize*0.65;
      ctx.strokeStyle='#111'; ctx.lineWidth=2;
      ctx.strokeRect(sx-hw,sy-hw,hw*2,hw*2);
      // 選択文字を黒太字で再描画（最前面）
      ctx.font=`bold ${fontSize}px "Hiragino Sans","Noto Sans CJK JP",sans-serif`;
      ctx.textAlign='center'; ctx.textBaseline='middle';
      ctx.fillStyle='#000';
      ctx.fillText(data.chars[selIdx], sx, sy);
    } else {
      // ドットモード: 黒リング
      ctx.strokeStyle='#111'; ctx.lineWidth=2;
      ctx.beginPath(); ctx.arc(sx,sy,8,0,Math.PI*2); ctx.stroke();
      const col=RAD_COLOR[data.radical[selIdx]]||'#333';
      ctx.fillStyle=col;
      ctx.beginPath(); ctx.arc(sx,sy,4,0,Math.PI*2); ctx.fill();
    }
  }
}

// ── パン・ズーム ──────────────────────────────────────────────────────────────
let panning=false, px0,py0,panX0,panY0, moved=false;

canvas.addEventListener('mousedown',e=>{
  if(e.button!==0)return;
  panning=true; moved=false;
  px0=e.clientX; py0=e.clientY; panX0=panX; panY0=panY;
  canvas.classList.add('panning');
});
document.addEventListener('mousemove',e=>{
  if(panning){
    const dx=e.clientX-px0, dy=e.clientY-py0;
    if(Math.abs(dx)+Math.abs(dy)>3) moved=true;
    panX=panX0+dx; panY=panY0+dy; scheduleRender();
  }
});
document.addEventListener('mouseup',e=>{
  if(!panning)return;
  panning=false; canvas.classList.remove('panning');
  if(!moved){
    const rect=canvas.getBoundingClientRect();
    const sx=e.clientX-rect.left, sy=e.clientY-rect.top;
    const i=findNearest(sx,sy);
    if(i>=0) selectChar(data.chars[i]);
  }
});
canvas.addEventListener('wheel',e=>{
  e.preventDefault();
  const rect=canvas.getBoundingClientRect();
  const mx=e.clientX-rect.left, my=e.clientY-rect.top;
  const f=e.deltaY<0?1.18:1/1.18;
  const ns=Math.max(0.4,Math.min(60,scale*f));
  panX=mx-(mx-panX)*ns/scale; panY=my-(my-panY)*ns/scale;
  scale=ns; scheduleRender();
},{passive:false});

// ── ツールチップ ──────────────────────────────────────────────────────────────
const tooltip=document.getElementById('tooltip');
let ttTimeout=null;
canvas.addEventListener('mousemove',e=>{
  if(panning){tooltip.style.display='none';return;}
  clearTimeout(ttTimeout);
  ttTimeout=setTimeout(()=>{
    const rect=canvas.getBoundingClientRect();
    const i=findNearest(e.clientX-rect.left, e.clientY-rect.top, 24);
    if(i>=0){
      const ch=data.chars[i], st=data.stroke[i];
      tooltip.textContent=`${ch}　画数 ${st||'?'}`;
      tooltip.style.left=(e.clientX-rect.left+14)+'px';
      tooltip.style.top =(e.clientY-rect.top -6)+'px';
      tooltip.style.display='block';
    } else { tooltip.style.display='none'; }
  },30);
});
canvas.addEventListener('mouseleave',()=>{ tooltip.style.display='none'; });

// ── 選択 ─────────────────────────────────────────────────────────────────────
async function selectChar(char){
  status(`検索中… ${char}`);
  const r=await fetch(`api/search?q=${encodeURIComponent(char)}&n=16`);
  const d=await r.json();
  if(d.error){status(d.error);return;}

  selIdx=d.idx;
  nbIdxs=d.neighbors.map(n=>n.idx);

  // 選択位置を画面中央に
  const sw=(W-PAD*2), sh=(H-PAD*2);
  panX=W/2-d.nx*sw*scale-PAD;
  panY=H/2-d.ny*sh*scale-PAD;
  scheduleRender();
  showPanel(d);
  status('');
}

async function doSearch(){
  const ch=document.getElementById('searchInput').value.trim();
  if(ch) await selectChar(ch);
}
document.getElementById('searchInput').addEventListener('keydown',e=>{
  if(e.key==='Enter') doSearch();
});

// ── 部首名マップ（GROUPS 以外は番号表示）────────────────────────────────────
const RAD_NAME = Object.fromEntries(GROUPS.map(g=>{
  const m = g.name.match(/[（(](.+)[）)]/);
  return [g.rad, m ? m[1] : g.name];
}));

// ── パネル表示 ───────────────────────────────────────────────────────────────
function showPanel(d){
  const radLabel = RAD_NAME[d.radical]
    ? `${d.radical}番（${RAD_NAME[d.radical]}）`
    : `${d.radical}番`;

  document.getElementById('sel-body').innerHTML=`
    <img id="sel-img" src="${d.image}" alt="${d.char}">
    <div id="sel-meta">
      <span id="sel-char-big">${d.char}</span>
      U+${d.char.codePointAt(0).toString(16).toUpperCase().padStart(4,'0')}<br>
      画数：${d.stroke||'?'}<br>
      部首：${radLabel}
    </div>`;

  // 同部首リスト
  const radArea  = document.getElementById('rad-area');
  const radTitle = document.getElementById('rad-title');
  const radChars = document.getElementById('rad-chars');
  if(d.same_rad && d.same_rad.length > 0){
    radTitle.textContent = `同じ部首の漢字（${d.same_rad.length}字）`;
    radChars.innerHTML = '';
    for(const ch of d.same_rad){
      const span = document.createElement('span');
      span.className = 'rad-ch';
      span.textContent = ch;
      span.addEventListener('click', ()=>selectChar(ch));
      radChars.appendChild(span);
    }
    radArea.style.display = '';
  } else {
    radArea.style.display = 'none';
  }

  const grid=document.getElementById('nb-grid');
  grid.innerHTML='';
  for(const nb of d.neighbors){
    const div=document.createElement('div');
    div.className='nb-item';
    div.innerHTML=`<img src="${nb.image}" alt="${nb.char}">
                   <span class="nb-char">${nb.char}</span>
                   <span class="nb-dist">${nb.dist.toFixed(2)}</span>`;
    div.addEventListener('click',()=>selectChar(nb.char));
    grid.appendChild(div);
  }
}

// ── 凡例 ─────────────────────────────────────────────────────────────────────
function buildLegend(){
  const leg=document.getElementById('legend');
  leg.innerHTML=GROUPS.map(g=>
    `<div class="leg-row"><div class="leg-dot" style="background:${g.color}"></div>${g.name}</div>`
  ).join('')+`<div class="leg-row" style="margin-top:3px;border-top:1px solid #e8e8e8;padding-top:4px;">
    <div class="leg-dot" style="background:#ccc"></div>その他</div>`;
}

function buildGroups(){
  const radSet=new Set(GROUPS.map(g=>g.rad));
  bgIdxs=[];
  GROUPS.forEach(g=>groupIdxs[g.rad]=[]);
  for(let i=0;i<N;i++){
    const r=data.radical[i];
    if(radSet.has(r)) groupIdxs[r].push(i);
    else bgIdxs.push(i);
  }
}

function status(msg){ document.getElementById('status').textContent=msg; }

// ── 初期化 ───────────────────────────────────────────────────────────────────
async function init(){
  const r=await fetch('api/data');
  data=await r.json();
  N=data.nx.length;
  buildGroups();
  buildLegend();
  // 初期スケール: データがほぼ画面に収まるように
  scale=0.85; panX=(W-PAD*2)*(1-scale)/2; panY=(H-PAD*2)*(1-scale)/2;
  resize();
  status(`${N.toLocaleString()}字 読み込み完了`);
  setTimeout(()=>status(''),2500);
}

window.addEventListener('resize',resize);
resize();
init();
</script>
</body>
</html>"""


# ── HTTP Handler ──────────────────────────────────────────────────────────────
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

        if p.path in ('/', '/index.html'):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode())

        elif p.path == '/api/data':
            self._json({
                "nx":      [round(float(v), 5) for v in _nx],
                "ny":      [round(float(v), 5) for v in _ny],
                "radical": [int(v) for v in _radicals],
                "stroke":  [int(v) for v in _strokes],
                "chars":   list(_chars),
            })

        elif p.path == '/api/search':
            q = parse_qs(p.query)
            char = q.get('q', [''])[0].strip()
            k    = min(int(q.get('n', [16])[0]), 32)
            if not char or char not in _char2idx:
                self._json({"error": f"「{char}」が見つかりません"}, 404)
                return
            idx = _char2idx[char]
            neighbors = []
            for ni, dist in knn(idx, k):
                nc = _chars[ni]
                neighbors.append({
                    "idx":     ni,
                    "char":    nc,
                    "nx":      round(float(_nx[ni]), 5),
                    "ny":      round(float(_ny[ni]), 5),
                    "radical": int(_radicals[ni]),
                    "stroke":  int(_strokes[ni]),
                    "dist":    round(dist, 4),
                    "image":   char_b64(nc),
                })
            rad = int(_radicals[idx])
            same_rad = [str(_chars[i]) for i in range(len(_chars))
                        if int(_radicals[i]) == rad and i != idx]
            self._json({
                "char":       char,
                "idx":        idx,
                "nx":         round(float(_nx[idx]), 5),
                "ny":         round(float(_ny[idx]), 5),
                "radical":    rad,
                "stroke":     int(_strokes[idx]),
                "image":      char_b64(char),
                "neighbors":  neighbors,
                "same_rad":   same_rad,
            })

        else:
            self.send_response(404); self.end_headers()


# ── 起動 ─────────────────────────────────────────────────────────────────────
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
