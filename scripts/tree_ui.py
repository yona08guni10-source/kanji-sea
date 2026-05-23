#!/usr/bin/env python3
"""
tree_ui.py — 漢字樹形図
========================
Port: 7864
"""
import base64, io, json, subprocess, sys, tempfile, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import torch
from PIL import Image

try:
    import cairosvg
    _CAIROSVG = True
except ImportError:
    _CAIROSVG = False

ROOT     = Path(__file__).parent.parent
CKPT     = ROOT / "models" / "kanji_sans" / "model_epoch1000.pt"
DATA_DIR = ROOT / "data"  / "noto_kanji_sans" / "kanji"
PORT     = 7864
SEED     = 42

sys.path.insert(0, str(ROOT / "scripts"))
from symbol_diffusion import SymbolUNet, load_char_image

DEVICE = ("mps" if torch.backends.mps.is_available() else
          "cuda" if torch.cuda.is_available() else "cpu")

print("モデル読み込み中…")
_state   = torch.load(CKPT, map_location=DEVICE, weights_only=True)
IMG_SIZE = _state.get("img_size", 64)
model    = SymbolUNet(img_size=IMG_SIZE, base_ch=_state.get("base_ch", 48)).to(DEVICE)
model.load_state_dict(_state["model"])
model.eval()
print(f"  epoch={_state.get('epoch')}  loss={_state.get('loss',0):.5f}")

VEC_SIZE = 256
_lock    = threading.Lock()
_nodes   = {}
_pending = {}
_nid     = [0]
_tmpdir  = Path(tempfile.mkdtemp(prefix="tree_ui_"))


def _new_id():
    _nid[0] += 1
    return f"n{_nid[0]}"

def _to_b64(tensor):
    arr = ((tensor.squeeze().cpu().numpy() + 1) * 127.5).clip(0, 255).astype(np.uint8)
    pil = Image.fromarray(arr, "L").resize((VEC_SIZE, VEC_SIZE), Image.LANCZOS)
    bw  = np.where(np.array(pil) < 160, 0, 255).astype(np.uint8)
    if _CAIROSVG:
        try:
            pbm = _tmpdir / "t.pbm"; svg = _tmpdir / "t.svg"
            Image.fromarray(bw, "L").save(str(pbm))
            subprocess.run(["potrace", "-s",
                            "-W", f"{VEC_SIZE}pt", "-H", f"{VEC_SIZE}pt",
                            "-o", str(svg), str(pbm)],
                           check=True, capture_output=True, timeout=10)
            png = cairosvg.svg2png(url=str(svg), background_color="white",
                                   output_width=VEC_SIZE, output_height=VEC_SIZE)
            return "data:image/png;base64," + base64.b64encode(png).decode()
        except Exception:
            pass
    buf = io.BytesIO()
    Image.fromarray(bw, "L").save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

def _kanji_b64(char):
    path = DATA_DIR / f"{ord(char):05X}.png"
    if not path.exists():
        return None
    buf = io.BytesIO()
    Image.open(path).convert("L").resize((VEC_SIZE, VEC_SIZE), Image.LANCZOS).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

def _strip(node):
    return {k: v for k, v in node.items() if k != "tensor"}

# ── 安定ハッシュ（PYTHONHASHSEED非依存）──────────────────────────────────────
def _stable_hash(s: str) -> int:
    """Python の hash() は起動ごとに変わるので DJB2 で代替。"""
    h = 5381
    for c in s:
        h = ((h << 5) + h + ord(c)) & 0xFFFFFFFF
    return h

# ── テンソル計算（共通） ──────────────────────────────────────────────────────
def _compute_tensor(nid_a, nid_b, blend, temperature, n_steps, seed_idx):
    """単一子のテンソルを計算（ID 管理なし）"""
    with _lock:
        na = _nodes.get(nid_a)
        nb = _nodes.get(nid_b) if nid_b else None
    img_a = na["tensor"].to(DEVICE)
    if nb is not None:
        img_b = nb["tensor"].to(DEVICE)
        x_center = ((1 - blend) * img_a + blend * img_b).clamp(-1, 1)
    else:
        x_center = img_a.clamp(-1, 1)
    eff_temp   = float(temperature)
    t_start    = 1.0 - eff_temp
    start_step = int(t_start * n_steps)
    dt         = 1.0 / n_steps
    base_seed  = (SEED ^ (_stable_hash(nid_a) * 2654435761)
                       ^ (_stable_hash(nid_b or "") * 2246822519)) & 0xFFFFFFFF
    torch.manual_seed((base_seed + seed_idx * 6364136223846793005) & 0xFFFFFFFF)
    noise = torch.randn(1, 1, IMG_SIZE, IMG_SIZE, device=DEVICE)
    with torch.no_grad():
        if eff_temp < 1e-6:
            z = x_center.unsqueeze(0)
        else:
            z = t_start * x_center.unsqueeze(0) + eff_temp * noise
            for step in range(start_step, n_steps):
                t_val = torch.full((1,), step * dt, device=DEVICE)
                z = z + model(z, t_val) * dt
    return z.clamp(-1, 1).squeeze(0).cpu()

# ── ノード操作 ────────────────────────────────────────────────────────────────
def _add_kanji(char, x, y, node_id=None):
    img  = load_char_image(char, DATA_DIR, IMG_SIZE)
    if img is None:
        return None
    nid  = node_id or _new_id()
    disp = _kanji_b64(char) or _to_b64(img)
    node = {"id": nid, "char": char, "label": char, "type": "kanji",
            "parent_a": None, "parent_b": None, "tensor": img, "image": disp,
            "x": x, "y": y}
    with _lock:
        _nodes[nid] = node
    return _strip(node)

def _generate(nid_a, nid_b, count, n_steps, blend=0.5, temperature=0.7):
    with _lock:
        na = _nodes.get(nid_a) or _pending.get(nid_a)
        nb = (_nodes.get(nid_b) or _pending.get(nid_b)) if nid_b else None
    if na is None:
        return None, "親Aが見つかりません"
    la = na.get("char") or na["label"]
    lb = (nb.get("char") or nb["label"]) if nb else None
    label = f"{la}×{lb}" if lb else f"{la}の子"
    results = []
    for i in range(count):
        z   = _compute_tensor(nid_a, nid_b, blend, temperature, n_steps, i)
        nid = _new_id()
        node = {"id": nid, "char": None, "label": label, "type": "generated",
                "parent_a": nid_a, "parent_b": nid_b,
                "blend": round(blend, 3), "temperature": round(temperature, 3),
                "seed_idx": i, "n_steps": n_steps,
                "tensor": z, "image": _to_b64(z), "x": 0, "y": 0}
        results.append(node)
    with _lock:
        for n in results:
            _pending[n["id"]] = n
    return [_strip(n) for n in results], None

def _adopt(nid, x, y):
    with _lock:
        node = _pending.pop(nid, None)
        if node is None:
            return None
        node["x"] = x; node["y"] = y
        node["image"] = _to_b64(node["tensor"])
        _nodes[nid] = node
    return _strip(node)

def _export():
    # "image" も含める → 読み込み時に再計算不要・完全復元
    KEEP = {"id","char","label","type","parent_a","parent_b",
            "blend","temperature","seed_idx","n_steps","x","y","image"}
    with _lock:
        return {"version": 3,
                "nodes": [{k:v for k,v in n.items() if k in KEEP}
                           for n in _nodes.values()]}

def _import(data):
    """保存 JSON からツリーを復元（テンソルを再計算）"""
    nodes_list = data.get("nodes", [])
    kanji  = [n for n in nodes_list if n.get("type") == "kanji"]
    gen    = [n for n in nodes_list if n.get("type") != "kanji"]

    # _nid カウンタをリセット
    max_num = 0
    for n in nodes_list:
        try: max_num = max(max_num, int(n["id"][1:]))
        except: pass
    with _lock:
        _nodes.clear(); _pending.clear()
        _nid[0] = max_num

    result = []
    for nd in kanji:
        r = _add_kanji(nd["char"], nd["x"], nd["y"], node_id=nd["id"])
        if r: result.append(r)

    # 親が揃うまでリトライ（トポロジカル順）
    remaining = list(gen)
    for _ in range(len(gen) + 1):
        if not remaining: break
        nxt = []
        for nd in remaining:
            pa, pb = nd.get("parent_a"), nd.get("parent_b")
            with _lock:
                ok = pa in _nodes and (pb is None or pb in _nodes)
            if not ok:
                nxt.append(nd); continue
            # 保存済み image があればテンソル再計算をスキップ（完全復元）
            saved_img = nd.get("image")
            if saved_img:
                # 表示用画像は保存済みをそのまま使う
                # tensor はダミー（親として使われる場合のみ再計算）
                z = _compute_tensor(pa, pb,
                                    nd.get("blend", 0.5), nd.get("temperature", 0.7),
                                    nd.get("n_steps", 50), nd.get("seed_idx", 0))
                display_img = saved_img
            else:
                z = _compute_tensor(pa, pb,
                                    nd.get("blend", 0.5), nd.get("temperature", 0.7),
                                    nd.get("n_steps", 50), nd.get("seed_idx", 0))
                display_img = _to_b64(z)
            node = {"id": nd["id"], "char": None, "label": nd.get("label","生成"),
                    "type": "generated", "parent_a": pa, "parent_b": pb,
                    "blend": nd.get("blend",0.5), "temperature": nd.get("temperature",0.7),
                    "seed_idx": nd.get("seed_idx",0), "n_steps": nd.get("n_steps",50),
                    "tensor": z, "image": display_img,
                    "x": nd["x"], "y": nd["y"]}
            with _lock: _nodes[nd["id"]] = node
            result.append(_strip(node))
        remaining = nxt
    return {"nodes": result}

def _reset():
    with _lock:
        _nodes.clear(); _pending.clear(); _nid[0] = 0


# ── HTML ──────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>漢字樹形図</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:sans-serif;background:#f0f0f0;display:flex;flex-direction:column;height:100vh;overflow:hidden;}

#header{display:flex;align-items:center;gap:8px;padding:8px 14px;
  background:#fff;border-bottom:1px solid #eee;flex-shrink:0;z-index:10;flex-wrap:wrap;}
h1{font-size:12px;letter-spacing:4px;color:#bbb;font-weight:400;}
#addInput{width:44px;font-size:20px;text-align:center;padding:3px 4px;
  border:1px solid #ccc;border-radius:3px;outline:none;}
.hbtn{padding:4px 11px;font-size:11px;border:1px solid #ccc;border-radius:3px;
  cursor:pointer;background:#fff;color:#555;}
.hbtn:hover{background:#f5f5f5;}
.hbtn.primary{background:#111;color:#fff;border-color:#111;}
.hbtn.primary:hover{background:#333;}
.hbtn.active{background:#111;color:#fff;border-color:#111;}
#status{font-size:11px;color:#bbb;}
#status.err{color:#e44;}
.sep{width:1px;height:18px;background:#eee;margin:0 2px;}
#zoomVal{font-size:11px;color:#aaa;min-width:36px;text-align:center;}

#tree{flex:1;position:relative;overflow:hidden;cursor:grab;background:#f0f0f0;}
#tree.panning{cursor:grabbing;}
#canvas{position:absolute;top:0;left:0;transform-origin:0 0;width:4000px;height:4000px;}
#edges{position:absolute;top:0;left:0;pointer-events:none;width:4000px;height:4000px;}

.node{position:absolute;display:flex;flex-direction:column;align-items:center;
  gap:3px;cursor:pointer;user-select:none;}
.node img{width:88px;height:88px;border:2px solid #ddd;border-radius:5px;
  display:block;background:#fff;}
.node.sel-a img{border-color:#d44;box-shadow:0 0 0 3px #d443;}
.node.sel-b img{border-color:#44d;box-shadow:0 0 0 3px #44d3;}
.node-label{font-size:10px;color:#aaa;max-width:96px;text-align:center;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.node-badge{font-size:9px;color:#fff;padding:1px 5px;border-radius:8px;
  position:absolute;top:-6px;left:-6px;pointer-events:none;}
.badge-a{background:#d44;}.badge-b{background:#44d;}

#controls{display:flex;align-items:center;gap:12px;padding:9px 14px;
  background:#fff;border-top:1px solid #eee;flex-shrink:0;flex-wrap:wrap;z-index:10;}
.slot{display:flex;align-items:center;gap:5px;padding:5px 10px;
  border:1px solid #e0e0e0;border-radius:4px;min-width:100px;
  cursor:pointer;font-size:12px;color:#aaa;transition:all .15s;}
.slot.a{border-color:#d44;color:#d44;}.slot.b{border-color:#44d;color:#44d;}
.sl-row{display:flex;align-items:center;gap:5px;font-size:11px;color:#999;}
.sl-row input[type=range]{accent-color:#111;width:68px;}
.sl-val{min-width:28px;text-align:right;color:#bbb;font-variant-numeric:tabular-nums;}
#genBtn{padding:6px 20px;background:#111;color:#fff;border:none;border-radius:3px;
  cursor:pointer;font-size:12px;}
#genBtn:hover:not(:disabled){background:#333;}
#genBtn:disabled{background:#ccc;cursor:default;}

#offspring{position:fixed;bottom:0;left:0;right:0;background:#fff;
  border-top:2px solid #111;padding:11px 14px 14px;display:none;z-index:50;
  box-shadow:0 -4px 20px rgba(0,0,0,.08);}
#off-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:9px;}
#off-title{font-size:12px;color:#888;}
#off-close{padding:3px 10px;background:none;border:1px solid #ddd;
  border-radius:3px;cursor:pointer;font-size:11px;color:#999;}
#off-list{display:flex;gap:9px;overflow-x:auto;padding-bottom:2px;}
.off-item{flex-shrink:0;cursor:pointer;display:flex;flex-direction:column;
  align-items:center;gap:3px;}
.off-item img{width:100px;height:100px;border:2px solid #e0e0e0;
  border-radius:5px;background:#fff;transition:border-color .15s;}
.off-item:hover img{border-color:#111;}
.off-item.used img{opacity:.3;pointer-events:none;}
.off-label{font-size:10px;color:#ccc;}
</style>
</head>
<body>

<div id="header">
  <h1>漢字樹形図</h1>
  <input id="addInput" type="text" placeholder="漢" maxlength="1">
  <button class="hbtn primary" onclick="addKanji()">＋</button>
  <div class="sep"></div>
  <button class="hbtn" onclick="zoomBy(1.2)">＋</button>
  <span id="zoomVal">100%</span>
  <button class="hbtn" onclick="zoomBy(1/1.2)">－</button>
  <button class="hbtn" onclick="resetView()" title="ビューリセット">⟳</button>
  <div class="sep"></div>
  <button id="edgeToggle" class="hbtn" onclick="toggleEdge()">曲線</button>
  <div class="sep"></div>
  <button class="hbtn" onclick="saveTree()">保存</button>
  <button class="hbtn" onclick="document.getElementById('loadInput').click()">読込</button>
  <input id="loadInput" type="file" accept=".json" style="display:none"
         onchange="loadTree(this)">
  <button class="hbtn" onclick="newTree()">新規</button>
  <button class="hbtn" onclick="autoLayout()" title="ツリーを自動整列">整列</button>
  <span id="status"></span>
</div>

<div id="tree">
  <div id="canvas">
    <svg id="edges"></svg>
  </div>
</div>

<div id="controls">
  <div class="slot" id="slotA" onclick="clearSlot('A')"><span id="slotA-lbl">親A</span></div>
  <div class="slot" id="slotB" onclick="clearSlot('B')"><span id="slotB-lbl">親B（任意）</span></div>
  <div class="sl-row" id="blendRow" style="display:none">
    A←B
    <input type="range" id="blendSl" min="0" max="1" value="0.5" step="0.05"
           oninput="document.getElementById('blendVal').textContent=(+this.value).toFixed(2)">
    <span class="sl-val" id="blendVal">0.50</span>
  </div>
  <div class="sl-row">
    温度
    <input type="range" id="tempSl" min="0.05" max="1.0" value="0.7" step="0.05"
           oninput="document.getElementById('tempVal').textContent=(+this.value).toFixed(2)">
    <span class="sl-val" id="tempVal">0.70</span>
  </div>
  <div class="sl-row">
    子の数
    <input type="range" id="countSl" min="1" max="9" value="5" step="1"
           oninput="document.getElementById('countVal').textContent=this.value">
    <span class="sl-val" id="countVal">5</span>
  </div>
  <div class="sl-row">
    品質
    <input type="range" id="stepsSl" min="10" max="200" value="50" step="10"
           oninput="document.getElementById('stepsVal').textContent=this.value">
    <span class="sl-val" id="stepsVal">50</span>
  </div>
  <button id="genBtn" onclick="generate()" disabled>生成</button>
</div>

<div id="offspring">
  <div id="off-header">
    <span id="off-title">生成結果</span>
    <button id="off-close" onclick="closeOffspring()">閉じる</button>
  </div>
  <div id="off-list"></div>
</div>

<script>
// ── 状態 ─────────────────────────────────────────────────────────────────────
const nodes = {};
let selA=null, selB=null;
let pending=[];
let dragging=null, dragOX=0, dragOY=0, didDrag=false;
let panning=false, panSX=0, panSY=0;
let scale=1.0, panX=0, panY=0;
let edgeStyle='curve';
const THUMB=88, ROW_H=180;
const sibCount={};

// ── ズーム/パン ────────────────────────────────────────────────────────────────
function applyTransform(){
  document.getElementById('canvas').style.transform=
    `translate(${panX}px,${panY}px) scale(${scale})`;
}
function zoomBy(f, cx, cy){
  const tree=document.getElementById('tree'), rect=tree.getBoundingClientRect();
  const mx=cx!==undefined?cx-rect.left:rect.width/2;
  const my=cy!==undefined?cy-rect.top :rect.height/2;
  const ns=Math.max(0.1,Math.min(5,scale*f));
  panX=mx-(mx-panX)*ns/scale; panY=my-(my-panY)*ns/scale; scale=ns;
  applyTransform();
  document.getElementById('zoomVal').textContent=Math.round(scale*100)+'%';
}
function resetView(){ scale=1;panX=0;panY=0;applyTransform();
  document.getElementById('zoomVal').textContent='100%';}

document.getElementById('tree').addEventListener('wheel',e=>{
  e.preventDefault();
  zoomBy(e.deltaY<0?1.15:1/1.15,e.clientX,e.clientY);
},{passive:false});

// ── パン（空白ドラッグ）──────────────────────────────────────────────────────
document.getElementById('tree').addEventListener('mousedown',e=>{
  if(e.target.closest('.node')) return;
  panning=true; panSX=e.clientX-panX; panSY=e.clientY-panY;
  document.getElementById('tree').classList.add('panning');
  e.preventDefault();
});

// ── 漢字追加 ─────────────────────────────────────────────────────────────────
async function addKanji(){
  const ch=document.getElementById('addInput').value.trim(); if(!ch) return;
  const roots=Object.values(nodes).filter(n=>n.type==='kanji');
  const x=60+roots.length*140, y=60;
  status('追加中…');
  const r=await fetch('api/add_kanji',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({char:ch,x,y})});
  const d=await r.json();
  if(d.error){status(d.error,true);return;}
  addNodeToTree(d); document.getElementById('addInput').value=''; status('');
}
document.getElementById('addInput').addEventListener('keydown',e=>{if(e.key==='Enter')addKanji();});

// ── 生成 ─────────────────────────────────────────────────────────────────────
async function generate(){
  if(!selA) return;
  const count=+document.getElementById('countSl').value;
  const n_steps=+document.getElementById('stepsSl').value;
  const blend=+document.getElementById('blendSl').value;
  const temperature=+document.getElementById('tempSl').value;
  document.getElementById('genBtn').disabled=true;
  status(`重力場サンプリング中… (${count}個)`);
  const r=await fetch('api/generate',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({parent_a:selA,parent_b:selB||null,count,n_steps,blend,temperature})});
  const d=await r.json();
  document.getElementById('genBtn').disabled=false; status('');
  if(d.error){status(d.error,true);return;}
  pending=d; showOffspring(d);
}

// ── 採用 ─────────────────────────────────────────────────────────────────────
async function adopt(nid){
  const pnode=pending.find(n=>n.id===nid); if(!pnode) return;
  const pa=nodes[pnode.parent_a], pb=pnode.parent_b?nodes[pnode.parent_b]:null;
  let x=200,y=280;
  if(pa){
    const key=`${pnode.parent_a}-${pnode.parent_b||''}`;
    const idx=sibCount[key]||0; sibCount[key]=idx+1;
    x=(pb?(pa.x+pb.x)/2:pa.x)+idx*160;
    y=(pb?Math.max(pa.y,pb.y):pa.y)+ROW_H;
  }
  const r=await fetch('api/adopt',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({id:nid,x,y})});
  const d=await r.json();
  if(d.error){status(d.error,true);return;}
  addNodeToTree(d);
  autoLayout();
  const el=document.querySelector(`.off-item[data-id="${nid}"]`);
  if(el) el.classList.add('used');
}

// ── Tree DOM ──────────────────────────────────────────────────────────────────
function addNodeToTree(node){
  nodes[node.id]=node;
  const canvas=document.getElementById('canvas');
  const div=document.createElement('div');
  div.className='node'; div.id='nd-'+node.id;
  div.style.left=node.x+'px'; div.style.top=node.y+'px';
  div.innerHTML=`<img src="${node.image}" draggable="false">`+
                `<div class="node-label">${node.label}</div>`;
  div.addEventListener('mousedown',e=>startDrag(e,node.id));
  div.addEventListener('click',()=>{if(!didDrag)clickNode(node.id);});
  canvas.appendChild(div);
  redrawEdges(); updateGenBtn();
}

// ── 選択 ─────────────────────────────────────────────────────────────────────
function clickNode(nid){
  if(selA===null){ selA=nid; }
  else if(selB===null&&nid!==selA){ selB=nid; }
  else { clearSlot('A');clearSlot('B');selA=nid; }
  refreshSlots(); updateGenBtn();
}
function clearSlot(w){ if(w==='A')selA=null; if(w==='B')selB=null;
  refreshSlots(); updateGenBtn(); }

function refreshSlots(){
  document.querySelectorAll('.node').forEach(el=>{
    el.classList.remove('sel-a','sel-b');
    el.querySelectorAll('.node-badge').forEach(b=>b.remove());
  });
  [['A',selA,'sel-a','badge-a'],['B',selB,'sel-b','badge-b']].forEach(([t,id,sc,bc])=>{
    if(!id) return;
    const el=document.getElementById('nd-'+id); if(!el) return;
    el.classList.add(sc);
    const b=document.createElement('div'); b.className='node-badge '+bc; b.textContent=t;
    el.appendChild(b);
  });
  const na=nodes[selA], nb=nodes[selB];
  document.getElementById('slotA').className='slot'+(selA?' a':'');
  document.getElementById('slotB').className='slot'+(selB?' b':'');
  document.getElementById('slotA-lbl').textContent=selA?`A: ${na.label}`:'親A';
  document.getElementById('slotB-lbl').textContent=selB?`B: ${nb.label}`:'親B（任意）';
}
function updateGenBtn(){
  document.getElementById('genBtn').disabled=!selA;
  document.getElementById('blendRow').style.display=(selA&&selB)?'flex':'none';
}

// ── エッジ ────────────────────────────────────────────────────────────────────
function toggleEdge(){
  edgeStyle=edgeStyle==='curve'?'line':'curve';
  const btn=document.getElementById('edgeToggle');
  btn.textContent=edgeStyle==='curve'?'曲線':'直線';
  btn.classList.toggle('active', edgeStyle==='line');
  redrawEdges();
}
function redrawEdges(){
  const svg=document.getElementById('edges'); svg.innerHTML='';
  for(const [nid,node] of Object.entries(nodes)){
    if(!node.parent_a&&!node.parent_b) continue;
    const ch=center(nid); if(!ch) continue;
    for(const [pid,col] of [[node.parent_a,'#c66'],[node.parent_b,'#66c']]){
      if(!pid) continue;
      const p=center(pid); if(!p) continue;
      const path=document.createElementNS('http://www.w3.org/2000/svg','path');
      if(edgeStyle==='line'){
        const my=(p.y+ch.y)/2;
        path.setAttribute('d',`M${p.x},${p.y} L${p.x},${my} L${ch.x},${my} L${ch.x},${ch.y}`);
      } else {
        const dy=(ch.y-p.y)*.55;
        path.setAttribute('d',`M${p.x},${p.y} C${p.x},${p.y+dy} ${ch.x},${ch.y-dy} ${ch.x},${ch.y}`);
      }
      path.setAttribute('stroke',col);
      path.setAttribute('stroke-width','1.5');
      path.setAttribute('fill','none');
      path.setAttribute('opacity',edgeStyle==='line'?'0.6':'0.45');
      svg.appendChild(path);
    }
  }
}
function center(nid){
  const el=document.getElementById('nd-'+nid); if(!el) return null;
  return{x:parseInt(el.style.left)+THUMB/2,y:parseInt(el.style.top)+THUMB/2};
}

// ── ドラッグ ──────────────────────────────────────────────────────────────────
function screenToCanvas(sx,sy){
  const rect=document.getElementById('tree').getBoundingClientRect();
  return{x:(sx-rect.left-panX)/scale, y:(sy-rect.top-panY)/scale};
}
function startDrag(e,nid){
  if(e.button!==0) return;
  dragging=document.getElementById('nd-'+nid); didDrag=false;
  const c=screenToCanvas(e.clientX,e.clientY);
  dragOX=c.x-(parseInt(dragging.style.left)||0);
  dragOY=c.y-(parseInt(dragging.style.top )||0);
  e.stopPropagation(); e.preventDefault();
}
document.addEventListener('mousemove',e=>{
  if(dragging){
    didDrag=true;
    const c=screenToCanvas(e.clientX,e.clientY);
    const x=Math.max(0,c.x-dragOX), y=Math.max(0,c.y-dragOY);
    dragging.style.left=x+'px'; dragging.style.top=y+'px';
    const nid=dragging.id.replace('nd-','');
    if(nodes[nid]){nodes[nid].x=x;nodes[nid].y=y;}
    redrawEdges();
  }
  if(panning){panX=e.clientX-panSX;panY=e.clientY-panSY;applyTransform();}
});
document.addEventListener('mouseup',()=>{
  dragging=null; panning=false;
  document.getElementById('tree').classList.remove('panning');
});

// ── 保存/読込/新規 ────────────────────────────────────────────────────────────
async function saveTree(){
  const r=await fetch('api/export');
  const blob=await r.blob();
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=url;
  a.download='kanji_tree_'+new Date().toISOString().slice(0,16).replace(/[T:]/g,'-')+'.json';
  a.click();
}
async function loadTree(input){
  const file=input.files[0]; if(!file) return;
  const text=await file.text();
  status('読込中… テンソル再計算に時間がかかります');
  const r=await fetch('api/import',{method:'POST',
    headers:{'Content-Type':'application/json'},body:text});
  const d=await r.json();
  if(d.error){status(d.error,true);input.value='';return;}
  document.querySelectorAll('.node').forEach(el=>el.remove());
  for(const k of Object.keys(nodes)) delete nodes[k];
  selA=null;selB=null;refreshSlots();updateGenBtn();
  d.nodes.forEach(addNodeToTree); autoLayout(); status('');
  input.value='';
}
async function newTree(){
  if(Object.keys(nodes).length&&!confirm('現在のツリーをリセットしますか？')) return;
  await fetch('api/reset',{method:'POST'});
  document.querySelectorAll('.node').forEach(el=>el.remove());
  for(const k of Object.keys(nodes)) delete nodes[k];
  selA=null;selB=null;pending=[];
  for(const k of Object.keys(sibCount)) delete sibCount[k];
  refreshSlots();updateGenBtn();redrawEdges();
  panX=0;panY=0;scale=1;applyTransform();
  document.getElementById('zoomVal').textContent='100%';
  status('新規ツリー');
}

// ── offspring panel ───────────────────────────────────────────────────────────
function showOffspring(items){
  const list=document.getElementById('off-list'); list.innerHTML='';
  items.forEach(n=>{
    const div=document.createElement('div');
    div.className='off-item';div.dataset.id=n.id;
    const lbl=n.parent_b?`T=${n.temperature} B=${n.blend}`:`T=${n.temperature}`;
    div.innerHTML=`<img src="${n.image}"><span class="off-label">${lbl} #${n.seed_idx+1}</span>`;
    div.addEventListener('click',()=>adopt(n.id));
    list.appendChild(div);
  });
  document.getElementById('off-title').textContent=
    `生成結果 ${items.length}個 — クリックで採用`;
  document.getElementById('offspring').style.display='block';
}
function closeOffspring(){
  document.getElementById('offspring').style.display='none'; pending=[];
}
function status(msg,isErr=false){
  const el=document.getElementById('status');
  el.textContent=msg; el.className=isErr?'err':'';
}

// ── 自動レイアウト ─────────────────────────────────────────────────────────────
function avgParentX(nid){
  const n=nodes[nid];
  const xs=[];
  if(n.parent_a&&nodes[n.parent_a]) xs.push(nodes[n.parent_a].x||0);
  if(n.parent_b&&nodes[n.parent_b]) xs.push(nodes[n.parent_b].x||0);
  return xs.length ? xs.reduce((a,b)=>a+b,0)/xs.length : -1e9;
}
function autoLayout(){
  const nids=Object.keys(nodes);
  if(!nids.length) return;

  // 親→子リスト構築
  const children={};
  nids.forEach(id=>children[id]=[]);
  nids.forEach(id=>{
    const n=nodes[id];
    if(n.parent_a&&nodes[n.parent_a]) children[n.parent_a].push(id);
    if(n.parent_b&&nodes[n.parent_b]&&n.parent_b!==n.parent_a) children[n.parent_b].push(id);
  });

  // BFS で深さ計算
  const depth={};
  nids.forEach(id=>depth[id]=-1);
  const roots=nids.filter(id=>!nodes[id].parent_a&&!nodes[id].parent_b);
  roots.forEach(id=>depth[id]=0);
  const queue=[...roots];
  while(queue.length){
    const nid=queue.shift();
    for(const cid of children[nid]){
      if(depth[cid]===-1){depth[cid]=depth[nid]+1;queue.push(cid);}
    }
  }
  nids.forEach(id=>{if(depth[id]===-1)depth[id]=0;});

  // 層ごとにグループ化
  const maxD=Math.max(...nids.map(id=>depth[id]));
  const layers=Array.from({length:maxD+1},()=>[]);
  nids.forEach(id=>layers[depth[id]].push(id));

  const W=110, H=170, MX=60, MY=60;

  for(let d=0;d<=maxD;d++){
    const ids=layers[d];
    // 親のxの平均でソート（前の層はすでに配置済み）
    ids.sort((a,b)=>avgParentX(a)-avgParentX(b));
    ids.forEach((id,i)=>{
      const x=MX+i*W, y=MY+d*H;
      nodes[id].x=x; nodes[id].y=y;
      const el=document.getElementById('nd-'+id);
      if(el){el.style.left=x+'px';el.style.top=y+'px';}
    });
  }
  redrawEdges();
}
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
        elif p.path == '/api/nodes':
            with _lock:
                self._json([_strip(n) for n in _nodes.values()])
        elif p.path == '/api/export':
            data = _export()
            body = json.dumps(data, ensure_ascii=False, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition",
                             'attachment; filename="kanji_tree.json"')
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length)) if length else {}
        p      = urlparse(self.path)

        if p.path == '/api/add_kanji':
            char = body.get("char", "").strip()
            if len(char) != 1:
                self._json({"error": "1文字必要"}, 400); return
            node = _add_kanji(char, int(body.get("x",200)), int(body.get("y",60)))
            if node is None:
                self._json({"error": f"「{char}」がデータに見つかりません"}, 400); return
            self._json(node)

        elif p.path == '/api/generate':
            nid_a       = body.get("parent_a")
            nid_b       = body.get("parent_b") or None
            count       = max(1, min(9,   int(body.get("count",       5))))
            n_steps     = max(5, min(200, int(body.get("n_steps",    50))))
            blend       = max(0.0, min(1.0, float(body.get("blend",  0.5))))
            temperature = max(0.05, min(1.0, float(body.get("temperature", 0.7))))
            results, err = _generate(nid_a, nid_b, count, n_steps, blend, temperature)
            if err:
                self._json({"error": err}, 400); return
            self._json(results)

        elif p.path == '/api/adopt':
            node = _adopt(body.get("id"),
                          int(body.get("x", 300)), int(body.get("y", 300)))
            if node is None:
                self._json({"error": "not found"}, 404); return
            self._json(node)

        elif p.path == '/api/import':
            result = _import(body)
            self._json(result)

        elif p.path == '/api/reset':
            _reset()
            self._json({"ok": True})

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
