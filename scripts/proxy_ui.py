#!/usr/bin/env python3
"""
proxy_ui.py — 記号の海 統合プロキシ
=====================================
全ツールを1ポート(7800)に統合。
パスベースルーティングで各ツールへプロキシ。

  /          → ホームページ
  /tsne/     → 漢字 t-SNE (7865)
  /tree/     → 漢字樹形図 (7864)
  /morph/    → 漢字モーフィング (7860)
  /chain/    → 漢字連鎖モーフィング (7863)
  /tetra/    → 正四面体 重力場 (7861)
  /sea/      → 記号の海 (7866)

Usage:
  python scripts/proxy_ui.py
  → http://localhost:7800
  → cloudflared tunnel --url http://localhost:7800
"""

import os, socket, threading, time, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(os.environ.get("PROXY_PORT", 7800))

# パス → バックエンドポートのルーティング
ROUTES = {
    '/tsne':  7865,
    '/tree':  7864,
    '/morph': 7868,
    '/chain': 7863,
    '/tetra': 7861,
    '/sea':   7866,
}

# ──────────────────────────────────────────────────────────────────────────────
# ホームページ HTML（リンクが /tool/ 形式になっている）
# ──────────────────────────────────────────────────────────────────────────────
HOME_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>記号の海</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root { --bg:#f7f7f5; --fg:#1a1a1a; --muted:#aaa; --border:#e0e0dc; }
html, body {
  min-height:100vh; background:var(--bg); color:var(--fg);
  font-family:'Hiragino Sans','Helvetica Neue',sans-serif; font-weight:300;
}
header {
  padding:64px 60px 48px; border-bottom:1px solid var(--border);
  display:flex; align-items:flex-end; justify-content:space-between;
}
.site-title { font-size:clamp(28px,4vw,46px); font-weight:300; letter-spacing:.18em; }
.site-sub { font-size:11px; letter-spacing:.3em; color:var(--muted); margin-top:10px; }
.author { font-size:11px; letter-spacing:.25em; color:var(--muted); }
main {
  padding:52px 60px 80px;
  display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:24px;
}
.card {
  display:block; text-decoration:none; color:inherit;
  background:#fff; border:1px solid var(--border); border-radius:2px;
  overflow:hidden; transition:box-shadow .2s,transform .2s,border-color .2s;
}
.card:hover { box-shadow:0 8px 32px rgba(0,0,0,.07); transform:translateY(-2px); border-color:#ccc; }
.thumb {
  width:100%; aspect-ratio:16/9; background:#f2f2f0;
  display:flex; align-items:center; justify-content:center;
  font-family:'Hiragino Sans',sans-serif; overflow:hidden;
}
.thumb svg { width:100%; height:100%; }
.card-body { padding:22px 24px 24px; border-top:1px solid var(--border); }
.card-en { font-size:9px; letter-spacing:.35em; color:var(--muted); text-transform:uppercase; margin-bottom:8px; }
.card-title { font-size:17px; font-weight:400; letter-spacing:.08em; margin-bottom:10px; }
.card-desc { font-size:11px; line-height:1.9; color:#888; }
.status { display:inline-block; width:6px; height:6px; border-radius:50%;
          background:#ddd; margin-right:6px; vertical-align:middle; }
.status.on { background:#4caf50; }
footer { padding:32px 60px; border-top:1px solid var(--border); font-size:10px; color:var(--muted); letter-spacing:.2em; }
</style>
</head>
<body>
<header>
  <div>
    <div class="site-title">記号の海</div>
    <div class="site-sub">Sea of Symbols — Kanji Diffusion Model</div>
  </div>
  <div class="author">安藤 昂宏</div>
</header>
<main id="grid">

<a class="card" href="/tsne/" target="_blank">
  <div class="thumb">
    <svg viewBox="0 0 320 180" xmlns="http://www.w3.org/2000/svg">
      <style>text{font-family:'Hiragino Sans',sans-serif;}</style>
      <g fill="#ddd" font-size="7">
        <text x="28" y="34">乙</text><text x="55" y="22">仁</text><text x="90" y="41">伝</text>
        <text x="130" y="28">佐</text><text x="168" y="45">侍</text><text x="248" y="52">倫</text>
        <text x="20" y="70">凡</text><text x="48" y="85">刀</text><text x="80" y="68">剣</text>
        <text x="150" y="72">功</text><text x="188" y="88">勉</text><text x="265" y="80">化</text>
        <text x="35" y="118">匹</text><text x="100" y="125">印</text><text x="255" y="128">厳</text>
        <text x="58" y="148">口</text><text x="135" y="152">史</text><text x="208" y="150">合</text>
      </g>
      <g fill="#cc2222" font-size="9">
        <text x="162" y="88">問</text><text x="177" y="101">閑</text><text x="153" y="103">閉</text>
        <text x="169" y="115">間</text><text x="157" y="76">門</text><text x="183" y="87">聞</text>
      </g>
      <g fill="#228822" font-size="9">
        <text x="62" y="55">木</text><text x="74" y="67">林</text><text x="54" y="68">森</text>
      </g>
      <g fill="#2255cc" font-size="9">
        <text x="238" y="140">海</text><text x="250" y="152">湖</text><text x="228" y="152">川</text>
      </g>
      <rect x="160" y="80" width="15" height="15" fill="none" stroke="#111" stroke-width="1.5"/>
      <line x1="167" y1="0" x2="167" y2="180" stroke="rgba(0,0,0,.06)" stroke-dasharray="3,5"/>
      <line x1="0" y1="87" x2="320" y2="87" stroke="rgba(0,0,0,.06)" stroke-dasharray="3,5"/>
    </svg>
  </div>
  <div class="card-body">
    <div class="card-en">Kanji t-SNE Explorer</div>
    <div class="card-title"><span class="status" id="s-tsne"></span>漢字 t-SNE 探索</div>
    <div class="card-desc">拡散モデルの内部空間に漢字を配置した地図。同じ部首を持つ全漢字の一覧も表示。</div>
  </div>
</a>

<a class="card" href="/tree/" target="_blank">
  <div class="thumb">
    <svg viewBox="0 0 320 180" xmlns="http://www.w3.org/2000/svg">
      <style>text{font-family:'Hiragino Sans',sans-serif;fill:#333;}</style>
      <text x="160" y="26" text-anchor="middle" font-size="14">木</text>
      <line x1="160" y1="30" x2="90" y2="66" stroke="#ddd" stroke-width="1"/>
      <line x1="160" y1="30" x2="230" y2="66" stroke="#ddd" stroke-width="1"/>
      <text x="86" y="78" text-anchor="middle" font-size="11">林</text>
      <text x="230" y="78" text-anchor="middle" font-size="11">桜</text>
      <line x1="90" y1="82" x2="50" y2="116" stroke="#e0e0e0" stroke-width="1"/>
      <line x1="90" y1="82" x2="128" y2="116" stroke="#e0e0e0" stroke-width="1"/>
      <text x="46" y="128" text-anchor="middle" fill="#888" font-size="10">森</text>
      <text x="128" y="128" text-anchor="middle" fill="#888" font-size="10">梅</text>
      <line x1="230" y1="82" x2="195" y2="116" stroke="#e0e0e0" stroke-width="1"/>
      <line x1="230" y1="82" x2="265" y2="116" stroke="#e0e0e0" stroke-width="1"/>
      <text x="193" y="128" text-anchor="middle" fill="#888" font-size="10">松</text>
      <text x="265" y="128" text-anchor="middle" fill="#888" font-size="10">竹</text>
      <line x1="46" y1="132" x2="30" y2="156" stroke="#ebebeb"/><text x="28" y="165" text-anchor="middle" fill="#bbb" font-size="9">楠</text>
      <line x1="46" y1="132" x2="62" y2="156" stroke="#ebebeb"/><text x="62" y="165" text-anchor="middle" fill="#bbb" font-size="9">椎</text>
      <line x1="265" y1="132" x2="250" y2="156" stroke="#ebebeb"/><text x="248" y="165" text-anchor="middle" fill="#bbb" font-size="9">槻</text>
      <line x1="265" y1="132" x2="280" y2="156" stroke="#ebebeb"/><text x="282" y="165" text-anchor="middle" fill="#bbb" font-size="9">欅</text>
    </svg>
  </div>
  <div class="card-body">
    <div class="card-en">Kanji Dendrogram</div>
    <div class="card-title"><span class="status" id="s-tree"></span>漢字樹形図</div>
    <div class="card-desc">モデル内部空間での類似度を階層的な樹形図として可視化。</div>
  </div>
</a>

<a class="card" href="/morph/" target="_blank">
  <div class="thumb" style="background:#fafafa;gap:16px;">
    <span style="font-size:52px;color:#222;opacity:.85;">道</span>
    <span style="font-size:16px;color:#ccc;">···</span>
    <span style="font-size:44px;color:#555;opacity:.4;">⿺</span>
    <span style="font-size:16px;color:#ccc;">···</span>
    <span style="font-size:52px;color:#222;opacity:.85;">器</span>
  </div>
  <div class="card-body">
    <div class="card-en">Kanji Morphing</div>
    <div class="card-title"><span class="status" id="s-morph"></span>漢字モーフィング</div>
    <div class="card-desc">2つ以上の漢字を選ぶと、その間を拡散モデルがなめらかに変形する動画を生成。</div>
  </div>
</a>

<a class="card" href="/chain/" target="_blank">
  <div class="thumb" style="background:#fafafa;">
    <div style="display:flex;align-items:center;gap:8px;">
      <span style="font-size:36px;color:#222;">記</span>
      <span style="color:#ddd;font-size:10px;">●●●</span>
      <span style="font-size:36px;color:#555;opacity:.6;">憶</span>
      <span style="color:#ddd;font-size:10px;">●●●</span>
      <span style="font-size:36px;color:#777;opacity:.35;">想</span>
      <span style="color:#ddd;font-size:10px;">●●●</span>
      <span style="font-size:36px;color:#999;opacity:.18;">像</span>
    </div>
  </div>
  <div class="card-body">
    <div class="card-en">Chain Morphing</div>
    <div class="card-title"><span class="status" id="s-chain"></span>漢字連鎖モーフィング</div>
    <div class="card-desc">文字列を入力すると各漢字を順にモーフィングしながらループ再生。</div>
  </div>
</a>

<a class="card" href="/tetra/" target="_blank">
  <div class="thumb">
    <svg viewBox="0 0 320 180" xmlns="http://www.w3.org/2000/svg">
      <style>text{font-family:'Hiragino Sans',sans-serif;}</style>
      <g stroke="#ccc" stroke-width="1" fill="none">
        <line x1="160" y1="28" x2="80" y2="145"/>
        <line x1="160" y1="28" x2="240" y2="145"/>
        <line x1="160" y1="28" x2="200" y2="90"/>
        <line x1="80" y1="145" x2="240" y2="145"/>
        <line x1="80" y1="145" x2="200" y2="90"/>
        <line x1="240" y1="145" x2="200" y2="90" stroke-dasharray="3,3"/>
      </g>
      <text x="160" y="22" text-anchor="middle" font-size="14" fill="#cc2222">喜</text>
      <text x="68" y="158" text-anchor="middle" font-size="14" fill="#2255cc">哀</text>
      <text x="250" y="158" text-anchor="middle" font-size="14" fill="#228822">楽</text>
      <text x="210" y="86" text-anchor="middle" font-size="14" fill="#cc7700">怒</text>
      <circle cx="158" cy="108" r="5" fill="#111" opacity=".6"/>
      <circle cx="158" cy="108" r="12" fill="none" stroke="#ccc" stroke-width="1"/>
      <text x="125" y="120" text-anchor="middle" font-size="22" fill="#555" opacity=".5">歓</text>
    </svg>
  </div>
  <div class="card-body">
    <div class="card-en">Tetrahedron Gravity Field</div>
    <div class="card-title"><span class="status" id="s-tetra"></span>正四面体 重力場</div>
    <div class="card-desc">喜怒哀楽を4頂点に配置した正四面体を3D操作。感情の混合を記号としてリアルタイム生成。</div>
  </div>
</a>

<a class="card" href="/sea/" target="_blank">
  <div class="thumb" style="background:#f5f5f5;">
    <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px;padding:14px;width:100%;">
      <span style="font-size:20px;text-align:center;opacity:.9">門</span>
      <span style="font-size:20px;text-align:center;opacity:.7">問</span>
      <span style="font-size:20px;text-align:center;opacity:.5">閑</span>
      <span style="font-size:20px;text-align:center;opacity:.8">間</span>
      <span style="font-size:20px;text-align:center;opacity:.4">闇</span>
      <span style="font-size:20px;text-align:center;opacity:.6">閉</span>
      <span style="font-size:20px;text-align:center;opacity:.3">閣</span>
      <span style="font-size:20px;text-align:center;opacity:.7">開</span>
      <span style="font-size:20px;text-align:center;opacity:.5">聞</span>
      <span style="font-size:20px;text-align:center;opacity:.9">悶</span>
      <span style="font-size:20px;text-align:center;opacity:.4">閥</span>
      <span style="font-size:20px;text-align:center;opacity:.8">闘</span>
      <span style="font-size:20px;text-align:center;opacity:.6">閲</span>
      <span style="font-size:20px;text-align:center;opacity:.3">関</span>
      <span style="font-size:20px;text-align:center;opacity:.6">闌</span>
      <span style="font-size:20px;text-align:center;opacity:.4">閏</span>
      <span style="font-size:20px;text-align:center;opacity:.8">閤</span>
      <span style="font-size:20px;text-align:center;opacity:.5">闕</span>
      <span style="font-size:20px;text-align:center;opacity:.7">閂</span>
      <span style="font-size:20px;text-align:center;opacity:.3">闃</span>
      <span style="font-size:20px;text-align:center;opacity:.6">閾</span>
    </div>
  </div>
  <div class="card-body">
    <div class="card-en">Sea of Symbols</div>
    <div class="card-title"><span class="status" id="s-sea"></span>記号の海</div>
    <div class="card-desc">漢字を選ぶとAIが次の漢字を選択しモーフィングしながら無限に流れ続けるインスタレーション。</div>
  </div>
</a>

</main>
<footer>記号の海 — 拡散モデルによる漢字記号生成 / 安藤 昂宏</footer>

<script>
// 各ツールの死活確認
const checks = [
  {id:'s-tsne',  path:'/tsne/api/data'},
  {id:'s-tree',  path:'/tree/api/ping'},
  {id:'s-morph', path:'/morph/'},
  {id:'s-chain', path:'/chain/'},
  {id:'s-tetra', path:'/tetra/'},
  {id:'s-sea',   path:'/sea/'},
];
async function checkStatus(){
  for(const c of checks){
    try{
      const r = await fetch(c.path, {signal: AbortSignal.timeout(1500)});
      document.getElementById(c.id).className = 'status ' + (r.ok ? 'on' : '');
    } catch { document.getElementById(c.id).className = 'status'; }
  }
}
checkStatus();
setInterval(checkStatus, 10000);
</script>
</body>
</html>"""


# ── プロキシ処理 ───────────────────────────────────────────────────────────────
def proxy_request(handler, backend_port: int, sub_path: str):
    """リクエストをバックエンドポートへ転送し、レスポンスをクライアントへ返す。"""
    target_url = f"http://127.0.0.1:{backend_port}{sub_path}"
    if handler.headers.get('Accept') == 'text/event-stream':
        # SSE: ストリーミング転送
        try:
            req = urllib.request.Request(
                target_url,
                headers={k: v for k, v in handler.headers.items()
                         if k.lower() not in ('host',)},
            )
            with urllib.request.urlopen(req, timeout=None) as resp:
                handler.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() in ('content-type', 'cache-control', 'connection'):
                        handler.send_header(k, v)
                handler.end_headers()
                while True:
                    chunk = resp.read(1024)
                    if not chunk:
                        break
                    handler.wfile.write(chunk)
                    handler.wfile.flush()
        except Exception:
            pass
        return

    try:
        req = urllib.request.Request(
            target_url,
            headers={k: v for k, v in handler.headers.items()
                     if k.lower() not in ('host', 'transfer-encoding')},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read()
            # HTML のみ: base タグを挿入してリソースパスを補正
            ct = resp.headers.get('Content-Type', '')
            if 'text/html' in ct:
                prefix = next(p for p, port in ROUTES.items() if port == backend_port)
                body = body.replace(
                    b'<head>', f'<head><base href="{prefix}/">'.encode(), 1
                )
            handler.send_response(resp.status)
            for k, v in resp.headers.items():
                if k.lower() in ('content-type', 'cache-control', 'access-control-allow-origin'):
                    handler.send_header(k, v)
            handler.send_header('Content-Length', str(len(body)))
            handler.send_header('Connection', 'keep-alive')
            handler.end_headers()
            handler.wfile.write(body)
    except urllib.error.URLError as e:
        msg = f'Tool not running: {e}'.encode()
        handler.send_response(503)
        handler.send_header('Content-Type', 'text/plain')
        handler.send_header('Content-Length', str(len(msg)))
        handler.end_headers()
        handler.wfile.write(msg)


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        # エラーのみ表示
        if args and str(args[1]) not in ('200', '304'):
            import sys
            print(f'  [{args[1]}] {self.path}', file=sys.stderr)

    def _route(self):
        path = self.path
        # ホーム
        if path in ('/', '/index.html'):
            return None, None
        # ルーティング
        for prefix, port in ROUTES.items():
            if path == prefix or path.startswith(prefix + '/'):
                sub = path[len(prefix):] or '/'
                return port, sub
        return None, None

    def do_GET(self):
        port, sub = self._route()
        if port is None and sub is None:
            body = HOME_HTML.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'keep-alive')
            self.end_headers()
            self.wfile.write(body)
        elif port:
            proxy_request(self, port, sub)
        else:
            self.send_response(404)
            self.send_header('Content-Length', '0')
            self.end_headers()

    def do_POST(self):
        port, sub = self._route()
        if port:
            length = int(self.headers.get('Content-Length', 0))
            body_data = self.rfile.read(length) if length else b''
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}{sub}",
                    data=body_data,
                    headers={k: v for k, v in self.headers.items()
                             if k.lower() not in ('host', 'transfer-encoding')},
                    method='POST',
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    body = resp.read()
                    self.send_response(resp.status)
                    for k, v in resp.headers.items():
                        if k.lower() in ('content-type', 'content-length'):
                            self.send_header(k, v)
                    self.end_headers()
                    self.wfile.write(body)
            except Exception:
                self.send_response(503)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == '__main__':
    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)

    # ローカルIPを表示
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = 'localhost'

    print(f"""
  記号の海 — 統合プロキシ起動
  ================================
  ローカル:      http://localhost:{PORT}
  同一LAN:       http://{local_ip}:{PORT}
  公開(要設定):  cloudflared tunnel --url http://localhost:{PORT}
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n終了')
