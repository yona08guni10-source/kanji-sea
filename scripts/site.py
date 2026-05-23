#!/usr/bin/env python3
"""
site.py — Nonsense Kanji ショーケースサイト
=============================================
静的ポートフォリオサイト。Gradio/モデル不要。
"""
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", 7860))

# ── 共通スタイル ───────────────────────────────────────────────────────────────
COMMON_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #f8f8f6;
  --fg: #111;
  --muted: #999;
  --border: #e0e0da;
  --white: #fff;
  --accent: #111;
}
html { scroll-behavior: smooth; }
body {
  background: var(--bg);
  color: var(--fg);
  font-family: 'Hiragino Sans', 'Noto Sans JP', 'Helvetica Neue', sans-serif;
  font-weight: 300;
  line-height: 1.7;
  min-height: 100vh;
}
a { color: inherit; text-decoration: none; }

/* ── ナビゲーション ── */
nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  background: rgba(248,248,246,0.92);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
  padding: 0 40px;
  height: 56px;
  display: flex; align-items: center; justify-content: space-between;
}
.nav-logo {
  font-size: 11px; letter-spacing: .4em; font-weight: 400;
  text-transform: uppercase; color: var(--fg);
}
.nav-author {
  font-size: 10px; letter-spacing: .3em; color: var(--muted);
}
.nav-back {
  font-size: 10px; letter-spacing: .25em; color: var(--muted);
  border: 1px solid var(--border); padding: 6px 16px;
  transition: border-color .2s, color .2s;
}
.nav-back:hover { border-color: #999; color: var(--fg); }

/* ── フッター ── */
footer {
  border-top: 1px solid var(--border);
  padding: 32px 40px;
  font-size: 10px; letter-spacing: .25em; color: var(--muted);
  display: flex; justify-content: space-between; align-items: center;
}
"""

# ── ホームページ ───────────────────────────────────────────────────────────────
HOME_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nonsense Kanji — 安藤昂宏</title>
<style>
""" + COMMON_CSS + """
/* ── ヒーロー ── */
.hero {
  padding: 160px 60px 80px;
  border-bottom: 1px solid var(--border);
}
.hero-group {
  font-size: 9px; letter-spacing: .55em; color: var(--muted);
  text-transform: uppercase; margin-bottom: 28px;
}
.hero-title {
  font-size: clamp(36px, 6vw, 72px);
  font-weight: 200; letter-spacing: .12em;
  line-height: 1.1; margin-bottom: 24px;
}
.hero-sub {
  font-size: 12px; letter-spacing: .2em; color: var(--muted);
  max-width: 480px; line-height: 2;
}
.hero-author {
  margin-top: 48px;
  font-size: 10px; letter-spacing: .35em; color: var(--muted);
}

/* ── グリッド ── */
.grid-section {
  padding: 72px 60px 100px;
}
.grid-label {
  font-size: 9px; letter-spacing: .5em; color: var(--muted);
  text-transform: uppercase; margin-bottom: 40px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 2px;
}

/* ── カード ── */
.card {
  display: block; background: var(--white);
  border: 1px solid var(--border);
  overflow: hidden;
  transition: transform .25s, box-shadow .25s, border-color .25s;
}
.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0,0,0,.08);
  border-color: #bbb;
}
.card-thumb {
  width: 100%; aspect-ratio: 16/9;
  background: #f2f2f0;
  overflow: hidden;
  display: flex; align-items: center; justify-content: center;
}
.card-thumb svg { width: 100%; height: 100%; }
.card-body { padding: 28px 28px 32px; border-top: 1px solid var(--border); }
.card-tag {
  font-size: 8px; letter-spacing: .4em; color: var(--muted);
  text-transform: uppercase; margin-bottom: 10px;
}
.card-title {
  font-size: 18px; font-weight: 400; letter-spacing: .06em;
  margin-bottom: 12px;
}
.card-desc {
  font-size: 11px; color: #888; line-height: 2;
}
.card-arrow {
  margin-top: 20px; font-size: 10px; letter-spacing: .2em; color: var(--muted);
}
</style>
</head>
<body>
<nav>
  <span class="nav-logo">Nonsense Kanji</span>
  <span class="nav-author">安藤 昂宏</span>
</nav>

<section class="hero">
  <div class="hero-group">Nonsense Kanji — Research &amp; Works</div>
  <h1 class="hero-title">非意味的<br>漢字の<br>記号空間</h1>
  <p class="hero-sub">拡散モデルが漢字の形を学習するとき、意味は不在のまま形だけが残る。<br>
  その内部空間を可視化し、意味の跳躍が起こりうる余白を探る。</p>
  <div class="hero-author">Takahiro Ando</div>
</section>

<section class="grid-section">
  <div class="grid-label">Works</div>
  <div class="grid">

    <!-- t-SNE -->
    <a class="card" href="tsne/">
      <div class="card-thumb">
        <svg viewBox="0 0 480 270" xmlns="http://www.w3.org/2000/svg">
          <rect width="480" height="270" fill="#f5f5f3"/>
          <style>text{font-family:'Hiragino Sans',sans-serif;}</style>
          <!-- 背景の点群 -->
          <g fill="#d8d8d5" font-size="9">
            <text x="40" y="50">乙</text><text x="80" y="34">仁</text>
            <text x="130" y="58">伝</text><text x="190" y="40">佐</text>
            <text x="250" y="62">侍</text><text x="380" y="74">倫</text>
            <text x="30" y="100">凡</text><text x="70" y="120">刀</text>
            <text x="120" y="96">剣</text><text x="220" y="104">功</text>
            <text x="280" y="125">勉</text><text x="410" y="112">化</text>
            <text x="50" y="168">匹</text><text x="150" y="178">印</text>
            <text x="390" y="185">厳</text><text x="80" y="210">口</text>
            <text x="200" y="218">史</text><text x="320" y="215">合</text>
            <text x="440" y="230">方</text><text x="15" y="240">亀</text>
            <text x="340" y="50">廉</text><text x="430" y="150">徒</text>
          </g>
          <!-- 門グループ（赤系）-->
          <g fill="#c0392b" font-size="13">
            <text x="230" y="126">問</text><text x="258" y="146">閑</text>
            <text x="210" y="148">閉</text><text x="238" y="166">間</text>
            <text x="218" y="110">門</text><text x="262" y="120">聞</text>
          </g>
          <!-- 木グループ（緑系）-->
          <g fill="#27ae60" font-size="13">
            <text x="92" y="80">木</text><text x="112" y="100">林</text>
            <text x="76" y="100">森</text><text x="98" y="120">桜</text>
          </g>
          <!-- 水グループ（青系）-->
          <g fill="#2980b9" font-size="13">
            <text x="354" y="196">海</text><text x="374" y="214">湖</text>
            <text x="334" y="210">川</text><text x="360" y="176">波</text>
          </g>
          <!-- フォーカス枠 -->
          <rect x="208" y="100" width="70" height="74" fill="none" stroke="#111" stroke-width="1.2" opacity=".4"/>
          <!-- 軸線 -->
          <line x1="240" y1="0" x2="240" y2="270" stroke="rgba(0,0,0,.04)" stroke-dasharray="4,6"/>
          <line x1="0" y1="135" x2="480" y2="135" stroke="rgba(0,0,0,.04)" stroke-dasharray="4,6"/>
          <!-- ラベル -->
          <text x="14" y="262" font-size="8" fill="#bbb" letter-spacing="2">t-SNE</text>
        </svg>
      </div>
      <div class="card-body">
        <div class="card-tag">01 — Visualization</div>
        <div class="card-title">漢字 t-SNE 探索</div>
        <div class="card-desc">拡散モデルの内部表現空間に全漢字を配置した地図。
        部首・字形の類似性が自然にクラスターを形成する。</div>
        <div class="card-arrow">詳細を見る →</div>
      </div>
    </a>

    <!-- 樹形図 -->
    <a class="card" href="tree/">
      <div class="card-thumb">
        <svg viewBox="0 0 480 270" xmlns="http://www.w3.org/2000/svg">
          <rect width="480" height="270" fill="#f5f5f3"/>
          <style>text{font-family:'Hiragino Sans',sans-serif;fill:#222;}</style>
          <!-- 樹形図 -->
          <text x="240" y="36" text-anchor="middle" font-size="18" font-weight="300">木</text>
          <line x1="240" y1="42" x2="140" y2="90" stroke="#ccc" stroke-width="1.2"/>
          <line x1="240" y1="42" x2="340" y2="90" stroke="#ccc" stroke-width="1.2"/>
          <text x="136" y="104" text-anchor="middle" font-size="14">林</text>
          <text x="340" y="104" text-anchor="middle" font-size="14">桜</text>
          <line x1="140" y1="110" x2="80" y2="155" stroke="#d8d8d8" stroke-width="1"/>
          <line x1="140" y1="110" x2="200" y2="155" stroke="#d8d8d8" stroke-width="1"/>
          <line x1="340" y1="110" x2="280" y2="155" stroke="#d8d8d8" stroke-width="1"/>
          <line x1="340" y1="110" x2="400" y2="155" stroke="#d8d8d8" stroke-width="1"/>
          <text x="76" y="168" text-anchor="middle" fill="#555" font-size="12">森</text>
          <text x="200" y="168" text-anchor="middle" fill="#555" font-size="12">梅</text>
          <text x="278" y="168" text-anchor="middle" fill="#555" font-size="12">松</text>
          <text x="400" y="168" text-anchor="middle" fill="#555" font-size="12">竹</text>
          <line x1="80" y1="174" x2="48" y2="210" stroke="#e8e8e8"/>
          <line x1="80" y1="174" x2="112" y2="210" stroke="#e8e8e8"/>
          <line x1="200" y1="174" x2="168" y2="210" stroke="#e8e8e8"/>
          <line x1="200" y1="174" x2="232" y2="210" stroke="#e8e8e8"/>
          <line x1="400" y1="174" x2="368" y2="210" stroke="#e8e8e8"/>
          <line x1="400" y1="174" x2="432" y2="210" stroke="#e8e8e8"/>
          <text x="46" y="222" text-anchor="middle" fill="#aaa" font-size="10">楠</text>
          <text x="112" y="222" text-anchor="middle" fill="#aaa" font-size="10">椎</text>
          <text x="168" y="222" text-anchor="middle" fill="#aaa" font-size="10">柿</text>
          <text x="232" y="222" text-anchor="middle" fill="#aaa" font-size="10">棟</text>
          <text x="368" y="222" text-anchor="middle" fill="#aaa" font-size="10">槻</text>
          <text x="432" y="222" text-anchor="middle" fill="#aaa" font-size="10">欅</text>
          <text x="14" y="262" font-size="8" fill="#bbb" letter-spacing="2">DENDROGRAM</text>
        </svg>
      </div>
      <div class="card-body">
        <div class="card-tag">02 — Analysis</div>
        <div class="card-title">漢字 樹形図</div>
        <div class="card-desc">モデルの内部距離をもとに漢字を階層クラスタリング。
        字形の近さが木構造として現れる。</div>
        <div class="card-arrow">詳細を見る →</div>
      </div>
    </a>

    <!-- モーフィング -->
    <a class="card" href="morph/">
      <div class="card-thumb">
        <svg viewBox="0 0 480 270" xmlns="http://www.w3.org/2000/svg">
          <rect width="480" height="270" fill="#f5f5f3"/>
          <style>text{font-family:'Hiragino Sans',sans-serif;}</style>
          <!-- モーフィング列 -->
          <text x="60" y="160" text-anchor="middle" font-size="64" fill="#111" opacity=".9">道</text>
          <text x="155" y="150" text-anchor="middle" font-size="10" fill="#ccc" letter-spacing="3">・・・</text>
          <text x="240" y="155" text-anchor="middle" font-size="52" fill="#555" opacity=".5">⿺</text>
          <text x="325" y="150" text-anchor="middle" font-size="10" fill="#ccc" letter-spacing="3">・・・</text>
          <text x="420" y="160" text-anchor="middle" font-size="64" fill="#111" opacity=".9">器</text>
          <!-- 中間フレームのヒント -->
          <text x="186" y="165" text-anchor="middle" font-size="36" fill="#888" opacity=".25">遠</text>
          <text x="294" y="165" text-anchor="middle" font-size="36" fill="#888" opacity=".25">周</text>
          <!-- ステップライン -->
          <line x1="80" y1="200" x2="400" y2="200" stroke="#e0e0da" stroke-width="1"/>
          <circle cx="80" cy="200" r="3" fill="#111"/>
          <circle cx="186" cy="200" r="2" fill="#ccc"/>
          <circle cx="240" cy="200" r="2" fill="#ccc"/>
          <circle cx="294" cy="200" r="2" fill="#ccc"/>
          <circle cx="400" cy="200" r="3" fill="#111"/>
          <text x="14" y="262" font-size="8" fill="#bbb" letter-spacing="2">MORPHING</text>
        </svg>
      </div>
      <div class="card-body">
        <div class="card-tag">03 — Generation</div>
        <div class="card-title">漢字 モーフィング</div>
        <div class="card-desc">2つの漢字を選ぶと、拡散モデルの潜在空間を補間しながら
        なめらかに変形する動画を生成する。</div>
        <div class="card-arrow">詳細を見る →</div>
      </div>
    </a>

  </div>
</section>

<footer>
  <span>Nonsense Kanji — 非意味的漢字の記号空間</span>
  <span>安藤 昂宏 / Takahiro Ando</span>
</footer>
</body>
</html>"""

# ── 詳細ページ共通テンプレート ─────────────────────────────────────────────────
def detail_page(num, tag, title_ja, title_en, desc_short, desc_long, tech_notes):
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_ja} — Nonsense Kanji</title>
<style>
{COMMON_CSS}
body {{ padding-top: 56px; }}
.page-hero {{
  padding: 80px 60px 60px;
  border-bottom: 1px solid var(--border);
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 60px;
  align-items: end;
}}
@media (max-width: 768px) {{ .page-hero {{ grid-template-columns: 1fr; }} }}
.page-num {{
  font-size: 9px; letter-spacing: .5em; color: var(--muted);
  text-transform: uppercase; margin-bottom: 16px;
}}
.page-title {{
  font-size: clamp(32px, 5vw, 56px);
  font-weight: 200; letter-spacing: .1em; line-height: 1.15;
}}
.page-en {{
  font-size: 11px; letter-spacing: .3em; color: var(--muted);
  margin-top: 16px; text-transform: uppercase;
}}
.page-desc-short {{
  font-size: 13px; line-height: 2; color: #555;
  align-self: end;
}}

/* ── 動画セクション ── */
.video-section {{
  padding: 72px 60px;
  border-bottom: 1px solid var(--border);
}}
.section-label {{
  font-size: 9px; letter-spacing: .5em; color: var(--muted);
  text-transform: uppercase; margin-bottom: 32px;
}}
.video-wrap {{
  width: 100%; max-width: 900px;
  aspect-ratio: 16/9;
  background: #111;
  position: relative;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
}}
.video-placeholder {{
  color: #444; font-size: 11px; letter-spacing: .3em;
  text-align: center;
}}
.video-wrap video {{
  width: 100%; height: 100%; object-fit: cover;
}}

/* ── 説明セクション ── */
.desc-section {{
  padding: 72px 60px;
  border-bottom: 1px solid var(--border);
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 80px;
}}
@media (max-width: 768px) {{ .desc-section {{ grid-template-columns: 1fr; }} }}
.desc-label {{
  font-size: 9px; letter-spacing: .5em; color: var(--muted);
  text-transform: uppercase;
}}
.desc-body {{
  font-size: 13px; line-height: 2.2; color: #444;
}}
.desc-body p + p {{ margin-top: 1.2em; }}

/* ── 技術ノート ── */
.tech-section {{
  padding: 60px 60px;
  border-bottom: 1px solid var(--border);
  background: var(--white);
}}
.tech-list {{
  margin-top: 24px;
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}}
.tech-item {{
  font-size: 10px; letter-spacing: .2em; color: var(--muted);
  padding: 12px 16px;
  border: 1px solid var(--border);
}}

/* ── 画像ギャラリー ── */
.gallery-section {{
  padding: 72px 60px;
}}
.gallery-grid {{
  margin-top: 32px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 2px;
}}
.gallery-item {{
  aspect-ratio: 4/3;
  background: #e8e8e4;
  display: flex; align-items: center; justify-content: center;
  font-size: 9px; letter-spacing: .3em; color: #bbb;
  text-transform: uppercase;
}}
</style>
</head>
<body>
<nav>
  <span class="nav-logo">Nonsense Kanji</span>
  <a class="nav-back" href="../">← 一覧に戻る</a>
</nav>

<section class="page-hero">
  <div>
    <div class="page-num">{num} — {tag}</div>
    <h1 class="page-title">{title_ja}</h1>
    <div class="page-en">{title_en}</div>
  </div>
  <p class="page-desc-short">{desc_short}</p>
</section>

<section class="video-section">
  <div class="section-label">Demo Video</div>
  <div class="video-wrap">
    <div class="video-placeholder">
      <div style="font-size:32px;margin-bottom:16px;opacity:.3">▶</div>
      <div>動画準備中 — Video Coming Soon</div>
    </div>
  </div>
</section>

<section class="desc-section">
  <div class="desc-label">Description</div>
  <div class="desc-body">{desc_long}</div>
</section>

<section class="tech-section">
  <div class="section-label">Technical Notes</div>
  <div class="tech-list">
    {''.join(f'<div class="tech-item">{t}</div>' for t in tech_notes)}
  </div>
</section>

<section class="gallery-section">
  <div class="section-label">Images</div>
  <div class="gallery-grid">
    <div class="gallery-item">Image 01</div>
    <div class="gallery-item">Image 02</div>
    <div class="gallery-item">Image 03</div>
  </div>
</section>

<footer>
  <span>Nonsense Kanji</span>
  <span>安藤 昂宏 / Takahiro Ando</span>
</footer>
</body>
</html>"""

# ── 各ページコンテンツ ─────────────────────────────────────────────────────────
PAGES = {
    "/tsne/": detail_page(
        num="01", tag="Visualization",
        title_ja="漢字 t-SNE 探索",
        title_en="Kanji t-SNE Explorer",
        desc_short="拡散モデルの内部空間に全漢字を配置した地図。同じ部首・字形の近さが、訓練なしに自然とクラスターを形成する。",
        desc_long="""<p>拡散モデルが漢字の形を学習するとき、意味は不在のままですが、内部表現には字形の相似性が蓄積されます。
        そのボトルネック特徴量を t-SNE で2次元に圧縮したとき、部首ごとのクラスターが自然に現れました。</p>
        <p>木・林・森が近くに集まり、門・問・閑が固まる。モデルはただ画素の配列を学んだだけですが、
        人間が長い時間をかけて作り上げた漢字の体系を内部に折りたたんでいます。</p>
        <p>漢字を1文字入力すると、その漢字の内部空間での座標と、最も近傍の漢字群を表示します。</p>""",
        tech_notes=["Diffusion Model (Flow Matching)", "t-SNE (perplexity=30)", "PCA-50 bottleneck", "20,992 Kanji", "numpy / scikit-learn"]
    ),
    "/tree/": detail_page(
        num="02", tag="Analysis",
        title_ja="漢字 樹形図",
        title_en="Kanji Dendrogram",
        desc_short="モデルの内部距離を使って漢字を階層クラスタリング。字形の近さが木構造として可視化される。",
        desc_long="""<p>漢字を選ぶと、その漢字を起点として周辺の漢字を内部空間での距離で階層化し、
        デンドログラム（樹形図）として描画します。</p>
        <p>どの漢字がどの漢字と「形が近い」のかを可視化する試みです。
        音読み・訓読み・意味とは無関係に、ただ形だけで結びついた漢字の親戚関係が現れます。</p>
        <p>漢字を追加していくと木が成長し、記号間の距離の地形が徐々に明らかになります。</p>""",
        tech_notes=["Diffusion Model (Flow Matching)", "Ward linkage clustering", "内部空間距離（PCA-50）", "インタラクティブ描画", "numpy / scipy"]
    ),
    "/morph/": detail_page(
        num="03", tag="Generation",
        title_ja="漢字 モーフィング",
        title_en="Kanji Morphing",
        desc_short="2つの漢字の間を拡散モデルの潜在空間で補間し、なめらかに変形する動画を生成する。",
        desc_long="""<p>「道」から「器」へ。2つの漢字の内部表現の間を線形補間しながら、
        各ステップで拡散モデルが画像を生成します。漢字が漢字を通過しながら変形する映像が生まれます。</p>
        <p>補間のステップ数・強度を調整することで、変形の速度や中間に出現する形を操作できます。
        意図しない漢字が経由地として現れることがあり、それ自体が記号の飛躍として面白い。</p>
        <p>連鎖モード（Chain Morphing）では文字列を入力すると各漢字を順にモーフィングしながらループ再生します。</p>""",
        tech_notes=["Diffusion Model (Flow Matching)", "潜在空間線形補間", "64×64 / 128×128px", "モデル: kanji_sans_epoch1000", "PyTorch / numpy"]
    ),
}

# ── HTTP サーバー ──────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if args and str(args[1]) not in ("200", "304"):
            import sys
            print(f"  [{args[1]}] {self.path}", file=sys.stderr)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send(HOME_HTML.encode(), "text/html; charset=utf-8")
        elif path in PAGES:
            self._send(PAGES[path].encode(), "text/html; charset=utf-8")
        elif path in ("/tsne", "/tree", "/morph"):
            # trailing slash redirect
            self._redirect(path + "/")
        else:
            body = b"Not Found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def _send(self, body, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location):
        self.send_response(301)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"\n  Nonsense Kanji — 起動\n  http://localhost:{PORT}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n終了")
