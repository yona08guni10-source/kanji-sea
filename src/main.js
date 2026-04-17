// ===== テーマリスト =====
const THEMES = [
  '誰かに会いたい', '怒りが収まらない', '何かが終わった', '新しいものが生まれる',
  'もう戻れない', '待ちわびている', '何かを失った', '誰かを傷つけた',
  '孤独でいたい', '声が出ない', '走り続けている', '静かに燃えている',
  '何かが始まろうとしている', '誰かを守りたい', '消えてしまいたい',
  'ここではないどこかへ', '時間が止まった', '何かに気づいた',
  '愛が重い', '悲しみが美しい', '怒りが力になる', '希望が見えない',
  '新しい自分になりたい', '古いものを手放す', '空白を埋めたい',
  '誰にも言えない', '全部わかってほしい', '何も感じなくなった',
  '終わりと始まりが重なる', '存在が揺らいでいる',
];

// ===== 読みつき漢字辞書（検索用）code → readings =====
// 読みのない漢字も文字直接入力で検索可能
const READINGS_MAP = new Map([
  ['0706b','ひ か かじ ほのお'],['06c34','みず すい'],['06728','き こ もく'],
  ['091d1','きん かね かな'],['0571f','つち ど'],['065e5','ひ にち じつ'],
  ['06708','つき げつ がつ'],['05c71','やま さん'],['05ddd','かわ せん'],
  ['06d77','うみ かい'],['07a7a','そら から くう'],['098a8','かぜ かざ ふう'],
  ['096e8','あめ あま う'],['096ea','ゆき せつ'],['082b1','はな か'],
  ['08349','くさ そう'],['068ee','もり しん'],['06797','はやし りん'],
  ['09ce5','とり ちょう'],['09b5a','さかな うお ぎょ'],['0866b','むし ちゅう'],
  ['077f3','いし せき しゃく こく'],['06ce2','なみ は'],['096f2','くも うん'],
  ['05149','ひかり こう'],['05f71','かげ えい'],['0661f','ほし せい しょう'],
  ['05915','ゆう せき'],['0671d','あさ ちょう'],['0591c','よる よ や'],
  ['07802','すな さ しゃ'],['0708e','ほのお えん'],['06c37','こおり ひょう'],
  ['09727','きり む'],['05d50','あらし'],['07159','けむり えん'],
  ['06ce1','あわ ほう'],['095c7','やみ あん'],
  ['04eba','ひと じん にん'],['0624b','て しゅ'],['076ee','め もく'],
  ['08033','みみ じ'],['053e3','くち こう'],['05fc3','こころ しん'],
  ['04f53','からだ たい てい'],['08840','ち けつ'],['09aa8','ほね こつ'],
  ['0982d','あたま とう ず'],['09854','かお がん'],['08db3','あし そく'],
  ['09996','くび しゅ'],['080cc','せ はい'],['08179','はら ふく'],
  ['06307','ゆび し'],['06bdb','け もう'],['076ae','かわ ひ'],
  ['080a9','かた けん'],['080f8','むね きょう'],['08170','こし よう'],
  ['06d99','なみだ るい'],['06c57','あせ かん'],['0606f','いき そく'],
  ['0611b','あい'],['060b2','かなし ひ'],['0559c','よろこ き'],
  ['06012','おこ いか ど'],['06050','おそ きょう'],['05e0c','まれ き'],
  ['0671b','のぞ ぼう もう'],['05922','ゆめ む'],['05b64','こ'],
  ['072ec','ひとり どく'],['0604b','こい れん'],['06016','こわ ふ'],
  ['054c0','あわれ あい'],['06182','うれ ゆう'],['0697d','たの らく がく'],
  ['082e6','くる にが く'],['075db','いた つう'],['05e78','しあわ こう'],
  ['0798f','ふく'],['060a9','なや のう'],['060c5','なさ じょう'],
  ['06b32','ほっ よく'],['09858','ねが がん'],['05ff5','ねん'],
  ['0610f','い'],['06065','はじ ち'],['05606','なげ たん'],
  ['06ce3','な きゅう'],['053eb','さけ きょう'],['07b11','わら しょう'],
  ['07720','ねむ みん'],['05fd8','わす ぼう'],['060f3','おも そう'],
  ['0751f','いき う は せい しょう'],['06b7b','し'],['0547d','いのち めい みょう'],
  ['09b42','たましい こん'],['09748','たま れい りょう'],['05728','あ ざい'],
  ['07121','な む'],['06709','あ ゆう う'],['0865a','うつ きょ こ'],
  ['0767d','しろ はく'],['09ed2','くろ こく'],['08d64','あか せき'],
  ['09752','あお せい'],['09ec4','き こう おう'],['07dd1','みどり りょく'],
  ['08272','いろ しょく'],['058f0','こえ せい しょう'],
  ['08a00','い こと げん'],['06587','ふみ ぶん'],['05b57','じ'],
  ['0672c','ほん もと'],['05f62','かたち けい'],['05540','な めい'],
  ['08a9e','かた ご'],
  ['08d70','はし そう'],['06765','く き らい'],['053bb','さ きょ'],
  ['0898b','み けん'],['0805e','き もん ぶん'],['077e5','し ち'],
  ['066f8','か しょ'],['0601d','おも し'],['08003','かんが こう'],
  ['08a71','はな わ'],['052d5','うご どう'],['07acb','た りつ'],
  ['08d77','お き'],['06d88','き しょう'],['073fe','あらわ げん'],
  ['05909','か へん'],['07d9a','つづ ぞく'],['065ad','た だん'],
  ['04e00','いち ひと'],['04e8c','に ふた'],['04e09','さん み'],
  ['056db','よん よ し'],['04e94','ご'],['0516d','ろく む'],
  ['04e03','なな しち'],['0516b','はち や'],['04e5d','きゅう く'],
  ['05341','じゅう と'],['0767e','ひゃく'],['05343','せん'],['04e07','まん ばん'],
  ['05927','おお だい たい'],['05c0f','ちい こ しょう'],['04e0a','うえ かみ じょう'],
  ['04e0b','した しも か げ'],['04e2d','なか ちゅう'],['05de6','ひだり さ'],
  ['053f3','みぎ う ゆう'],['0524d','まえ ぜん'],['05f8c','うしろ のち こう'],
  ['05185','うち ない'],['05916','そと がい'],['09593','あいだ ま かん'],
  ['0529b','ちから りき りょく'],['05200','かたな とう'],['05203','は にん'],
  ['05263','つるぎ けん'],['077e2','や し'],['06c17','き け'],
  ['09580','かど もん'],['056fd','くに こく'],['09053','みち どう'],
  ['05834','ば じょう'],['05bb6','いえ や か'],['0753a','まち ちょう'],
  ['07530','た でん'],['05e74','とし ねん'],['06642','とき じ'],
  ['0738b','おう'],['05e1d','みかど てい'],['0795e','かみ しん'],
  ['09b3c','おに き'],['09f8d','りゅう'],
]);

// ===== インスタンスカラー =====
const INSTANCE_COLORS = ['#c44', '#1155cc', '#228822', '#9933aa', '#cc7700'];

// ===== 漢字リスト（動的生成） =====
// サーバーから全コードを取得してリストを構築する
// KANJI_LIST = [[char, code, readings|undefined], ...]
let KANJI_LIST = [];

async function initKanjiList() {
  try {
    const res = await fetch('/api/kanji-codes');
    const codes = await res.json();
    KANJI_LIST = codes.map(code => {
      const cp   = parseInt(code, 16);
      const char = String.fromCodePoint(cp);
      const readings = READINGS_MAP.get(code);
      return [char, code, readings];
    });
    // 最初のピッカーにデータを流す
    const grid = document.querySelector('#picker-pop-0 .picker-grid');
    if (grid) renderPickerGrid(grid, '');
  } catch (e) {
    console.warn('漢字リスト取得失敗:', e.message);
  }
}

// ===== セッション =====
const SESSION_ID = crypto.randomUUID();
let lastSymbolId = null;  // 直前に保存した記号のID（連鎖追跡用）

// ===== AI生成追跡 =====
let aiSnapshot = null; // AI生成直後のスナップショット {theme, instances:[{char,code,removedIndices,transform}]}

// ===== 状態 =====
let currentTheme = '';
let kanjiData    = null;           // ロード済みデータ（単一）
let selectedCode = '0706b';        // 現在選択中のコード

let placedKanji = [];
let activeId    = null;
let nextId      = 0;
let markedStrokes       = new Set(); // 範囲選択でマークされた筆画 "instId:strokeIdx"
let selectionBaseScales = new Map(); // 選択時点の各インスタンスのスケール {scale,scaleX,scaleY}
let selFrameBBox        = null;      // 選択フレームのSVG座標 {x,y,w,h}
let handleDrag          = null;      // ハンドルドラッグ状態

// ===== 履歴（Undo/Redo） =====
let history    = [[]];
let historyIdx = 0;

function deepCopy(arr) { return JSON.parse(JSON.stringify(arr)); }

function pushHistory() {
  history = history.slice(0, historyIdx + 1);
  history.push(deepCopy(placedKanji));
  if (history.length > 60) history.shift();
  historyIdx = history.length - 1;
  syncHistoryBtns();
}

function undo() {
  if (historyIdx <= 0) return;
  historyIdx--;
  placedKanji = deepCopy(history[historyIdx]);
  activeId = null;
  renderCanvas();
  noActive.style.display = 'block';
  activePanel.style.display = 'none';
  syncHistoryBtns();
}

function redo() {
  if (historyIdx >= history.length - 1) return;
  historyIdx++;
  placedKanji = deepCopy(history[historyIdx]);
  activeId = null;
  renderCanvas();
  noActive.style.display = 'block';
  activePanel.style.display = 'none';
  syncHistoryBtns();
}

function syncHistoryBtns() {
  document.getElementById('btn-undo').disabled = historyIdx <= 0;
  document.getElementById('btn-redo').disabled = historyIdx >= history.length - 1;
}

// ===== DOM参照 =====
const canvas      = document.getElementById('canvas');
const themeText   = document.getElementById('theme-text');
const themeInput  = document.getElementById('theme-input');
const activePanel = document.getElementById('active-panel');
const noActive    = document.getElementById('no-active');
const activeTitle = document.getElementById('active-title');
const slX  = document.getElementById('sl-x');
const slY  = document.getElementById('sl-y');
const slR  = document.getElementById('sl-r');
const slS  = document.getElementById('sl-s');
const slSX = document.getElementById('sl-sx');
const slSY = document.getElementById('sl-sy');
const valX  = document.getElementById('val-x');
const valY  = document.getElementById('val-y');
const valR  = document.getElementById('val-r');
const valS  = document.getElementById('val-s');
const valSX = document.getElementById('val-sx');
const valSY = document.getElementById('val-sy');
const strokeList    = document.getElementById('stroke-list');
const strokeSummary = document.getElementById('stroke-summary');
const saveStatus    = document.getElementById('save-status');

// ===== お題 =====
const CUSTOM_THEMES_KEY = 'ids_custom_themes';

function loadCustomThemes() {
  try { return JSON.parse(localStorage.getItem(CUSTOM_THEMES_KEY)) || []; }
  catch { return []; }
}
function saveCustomThemes(list) {
  localStorage.setItem(CUSTOM_THEMES_KEY, JSON.stringify(list));
}

function buildThemeSelect() {
  const sel = document.getElementById('theme-select');
  const current = sel.value;
  sel.innerHTML = '<option value="">— 選択 —</option>';

  const custom = loadCustomThemes();
  if (custom.length) {
    const grpCustom = document.createElement('optgroup');
    grpCustom.label = 'マイお題';
    custom.forEach(t => {
      const opt = document.createElement('option');
      opt.value = opt.textContent = t;
      grpCustom.appendChild(opt);
    });
    sel.appendChild(grpCustom);
  }

  const grpDefault = document.createElement('optgroup');
  grpDefault.label = 'プリセット';
  THEMES.forEach(t => {
    const opt = document.createElement('option');
    opt.value = opt.textContent = t;
    grpDefault.appendChild(opt);
  });
  sel.appendChild(grpDefault);

  // 選択状態を復元
  if (current) sel.value = current;
}

function selectTheme(theme) {
  currentTheme = theme;
  themeText.textContent = theme || '—';
  updateThemeCount();
}

document.getElementById('theme-select').addEventListener('change', e => {
  if (e.target.value) selectTheme(e.target.value);
});

document.getElementById('btn-add-theme').addEventListener('click', () => {
  const v = document.getElementById('theme-input').value.trim();
  if (!v) return;
  const custom = loadCustomThemes();
  if (!custom.includes(v)) {
    custom.unshift(v);
    saveCustomThemes(custom);
    buildThemeSelect();
  }
  document.getElementById('theme-select').value = v;
  selectTheme(v);
  document.getElementById('theme-input').value = '';
});

document.getElementById('theme-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') document.getElementById('btn-add-theme').click();
});

buildThemeSelect();

// ===== 漢字ピッカー（単一） =====
{
  const btn    = document.getElementById('picker-btn-0');
  const pop    = document.getElementById('picker-pop-0');
  const search = pop.querySelector('.picker-search');
  const grid   = pop.querySelector('.picker-grid');

  btn.addEventListener('click', e => {
    e.stopPropagation();
    const wasOpen = !pop.hidden;
    closeAllPickers();
    if (!wasOpen) {
      pop.hidden = false;
      search.value = '';
      renderPickerGrid(grid, '');
      search.focus();
    }
  });
  search.addEventListener('input', () => renderPickerGrid(grid, search.value.trim()));
  pop.addEventListener('click', e => e.stopPropagation());
}

function closeAllPickers() {
  document.querySelectorAll('.picker-popover').forEach(p => { p.hidden = true; });
}
document.addEventListener('click', closeAllPickers);
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeAllPickers();
});

function renderPickerGrid(grid, query) {
  const q = query.trim().toLowerCase();
  const filtered = q
    ? KANJI_LIST.filter(([char,, readings]) =>
        char === q || (readings && readings.includes(q)))
    : KANJI_LIST;

  grid.innerHTML = '';
  filtered.slice(0, 120).forEach(([char, code]) => {
    const b = document.createElement('button');
    b.className = 'picker-kanji' + (code === selectedCode ? ' selected' : '');
    b.textContent = char;
    b.title = char;
    b.addEventListener('click', () => {
      selectedCode = code;
      document.getElementById('picker-btn-0').textContent = char;
      closeAllPickers();
      loadKanji(code);
    });
    grid.appendChild(b);
  });
  if (filtered.length > 120) {
    const more = document.createElement('div');
    more.className = 'picker-more';
    more.textContent = `他 ${filtered.length - 120} 件…`;
    grid.appendChild(more);
  }
}

// ===== 漢字SVGロード =====
async function loadKanji(code) {
  if (!code) { kanjiData = null; return; }
  try {
    const res = await fetch(`/data/kanjivg/kanji_${code}.svg`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const text = await res.text();
    const entry = parseKanjiSVG(text);
    const found = KANJI_LIST.find(([, c]) => c === code);
    entry.char = found ? found[0] : '?';
    entry.code = code;
    kanjiData = entry;
  } catch (e) {
    kanjiData = null;
    console.warn('読み込み失敗:', e.message);
  }
}

function parseKanjiSVG(svgText) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(svgText, 'image/svg+xml');
  return {
    paths: Array.from(doc.querySelectorAll('path')).map((p, i) => ({
      d: p.getAttribute('d'), index: i,
    }))
  };
}

// ===== 追加ボタン =====
document.getElementById('btn-add-kanji').addEventListener('click', addKanji);

// ===== 漢字の重心計算 =====
function getKanjiCenter(paths) {
  const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  g.setAttribute('visibility', 'hidden');
  paths.forEach(p => {
    const el = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    el.setAttribute('d', p.d);
    g.appendChild(el);
  });
  canvas.appendChild(g);
  const bb = g.getBBox();
  canvas.removeChild(g);
  return { cx: bb.x + bb.width / 2, cy: bb.y + bb.height / 2 };
}

// ===== 漢字をキャンバスに追加 =====
async function addKanji() {
  if (!selectedCode) return;
  if (!kanjiData) await loadKanji(selectedCode);
  const data = kanjiData;
  if (!data) return;

  const colorIdx = nextId % INSTANCE_COLORS.length;
  const { cx, cy } = getKanjiCenter(data.paths);
  const instance = {
    id: nextId++,
    char: data.char,
    code: data.code,
    color: INSTANCE_COLORS[colorIdx],
    tx: 0, ty: 0, rotate: 0, scale: 1, scaleX: 1, scaleY: 1, spreadX: 0, spreadY: 0,
    cx, cy,
    strokes: data.paths.map((p, i) => ({
      index: i, d: p.d, op: 'keep',
    })),
  };

  placedKanji.push(instance);
  aiSnapshot = null; // 手動追加はAI生成扱いをリセット
  hideAiScorePanel();
  pushHistory();
  renderCanvas();
  setActive(instance.id);
}

// ===== キャンバス描画 =====
function renderCanvas() {
  canvas.querySelectorAll('.kanji-instance').forEach(el => el.remove());

  for (const inst of placedKanji) {
    const ns = 'http://www.w3.org/2000/svg';
    const g = document.createElementNS(ns, 'g');
    g.classList.add('kanji-instance');
    g.dataset.id = inst.id;
    g.setAttribute('transform', makeTransform(inst));
    g.style.cursor = 'grab';

    const isActive = inst.id === activeId;
    const sw = isActive ? '3.2' : '2.5';

    // ── 膜（membrane）: ベクターパスに沿った半透明ブロブ ──
    const membraneG = document.createElementNS(ns, 'g');
    membraneG.style.pointerEvents = 'none';
    for (const stroke of inst.strokes) {
      if (stroke.op === 'remove') continue;
      const mp = document.createElementNS(ns, 'path');
      mp.setAttribute('d', stroke.d);
      mp.setAttribute('fill', 'none');
      mp.setAttribute('stroke', inst.color);
      mp.setAttribute('stroke-width', '8');
      mp.setAttribute('stroke-linecap', 'round');
      mp.setAttribute('stroke-linejoin', 'round');
      mp.setAttribute('opacity', '0.09');
      membraneG.appendChild(mp);
    }
    g.appendChild(membraneG);

    for (const stroke of inst.strokes) {
      if (stroke.op === 'remove') continue;
      const key = `${inst.id}:${stroke.index}`;
      const isMarkedStroke = markedStrokes.has(key);

      // マーク済みの場合は赤いハローを先に描く
      if (isMarkedStroke) {
        const halo = document.createElementNS(ns, 'path');
        halo.setAttribute('d', stroke.d);
        halo.setAttribute('fill', 'none');
        halo.setAttribute('stroke', '#cc0000');
        halo.setAttribute('stroke-width', '7');
        halo.setAttribute('stroke-linecap', 'round');
        halo.setAttribute('stroke-linejoin', 'round');
        halo.setAttribute('opacity', '0.35');
        halo.style.pointerEvents = 'none';
        g.appendChild(halo);
      }

      const path = document.createElementNS(ns, 'path');
      path.setAttribute('d', stroke.d);
      path.setAttribute('fill', 'none');
      path.setAttribute('stroke', isMarkedStroke ? '#cc0000' : inst.color);
      path.setAttribute('stroke-width', sw);
      path.setAttribute('stroke-linecap', 'round');
      path.setAttribute('stroke-linejoin', 'round');
      path.classList.add('stroke-path');
      path.dataset.instId     = inst.id;
      path.dataset.strokeIdx  = stroke.index;
      g.appendChild(path);

      if (stroke.op === 'duplicate') {
        const dup = path.cloneNode();
        dup.setAttribute('opacity', '0.45');
        dup.setAttribute('transform', 'translate(2.5,2.5)');
        g.appendChild(dup);
      }
    }

    canvas.appendChild(g);
    applySpread(g, inst);

    // アクティブ時の強調ボーダー（矩形）
    if (isActive) {
      try {
        const bb = g.getBBox();
        if (bb.width > 0 || bb.height > 0) {
          const pad = 5;
          const rect = document.createElementNS(ns, 'rect');
          rect.setAttribute('x', (bb.x - pad).toFixed(2));
          rect.setAttribute('y', (bb.y - pad).toFixed(2));
          rect.setAttribute('width',  (bb.width  + pad * 2).toFixed(2));
          rect.setAttribute('height', (bb.height + pad * 2).toFixed(2));
          rect.setAttribute('fill', 'none');
          rect.setAttribute('stroke', inst.color);
          rect.setAttribute('stroke-width', '1.0');
          rect.setAttribute('stroke-dasharray', '2.5,1.5');
          rect.setAttribute('opacity', '0.75');
          rect.setAttribute('rx', '3');
          rect.style.pointerEvents = 'none';
          g.appendChild(rect);
        }
      } catch (_) {}
    }

    g.addEventListener('click', e => { e.stopPropagation(); setActive(inst.id); });
    g.addEventListener('mousedown', e => startDrag(e, inst.id));
  }

  // 選択フレームは削除のみ（再描画は呼び出し元が責任を持つ）
  removeSelectionFrame();

  // 使用中の漢字を表示
  const visible = placedKanji.filter(inst => inst.strokes.some(s => s.op !== 'remove'));
  document.getElementById('canvas-chars').textContent = visible.map(i => i.char).join('');
}

// ===== 選択フレーム＋ハンドル =====
function clientToSVG(x, y) {
  const pt = canvas.createSVGPoint();
  pt.x = x; pt.y = y;
  return pt.matrixTransform(canvas.getScreenCTM().inverse());
}

function removeSelectionFrame() {
  document.getElementById('selection-frame')?.remove();
  selFrameBBox = null;
}

function renderSelectionFrame() {
  removeSelectionFrame();
  if (markedStrokes.size === 0) return;

  // マーク済みパスのスクリーン矩形を SVG 座標に変換して合算
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  canvas.querySelectorAll('.stroke-path').forEach(path => {
    const key = `${path.dataset.instId}:${path.dataset.strokeIdx}`;
    if (!markedStrokes.has(key)) return;
    const r = path.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    const tl = clientToSVG(r.left, r.top);
    const br = clientToSVG(r.right, r.bottom);
    minX = Math.min(minX, tl.x); minY = Math.min(minY, tl.y);
    maxX = Math.max(maxX, br.x); maxY = Math.max(maxY, br.y);
  });
  if (minX === Infinity) return;

  const pad = 2.5;
  minX -= pad; minY -= pad; maxX += pad; maxY += pad;
  const w = maxX - minX, h = maxY - minY;
  selFrameBBox = { minX, minY, maxX, maxY, w, h };

  const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  g.id = 'selection-frame';
  g.style.pointerEvents = 'none';

  // 外枠（破線）
  const border = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
  border.setAttribute('x', minX); border.setAttribute('y', minY);
  border.setAttribute('width', w); border.setAttribute('height', h);
  border.setAttribute('fill', 'rgba(200,0,0,0.04)');
  border.setAttribute('stroke', '#c00');
  border.setAttribute('stroke-width', '0.6');
  border.setAttribute('stroke-dasharray', '2,1.5');
  border.style.pointerEvents = 'none';
  g.appendChild(border);

  // ハンドル定義: [id, x, y, cursor, scalesX, scalesY]
  const cx = minX + w / 2, cy = minY + h / 2;
  const handles = [
    ['tl', minX, minY, 'nw-resize', true,  true ],
    ['tm', cx,   minY, 'n-resize',  false, true ],
    ['tr', maxX, minY, 'ne-resize', true,  true ],
    ['ml', minX, cy,   'w-resize',  true,  false],
    ['mr', maxX, cy,   'e-resize',  true,  false],
    ['bl', minX, maxY, 'sw-resize', true,  true ],
    ['bm', cx,   maxY, 's-resize',  false, true ],
    ['br', maxX, maxY, 'se-resize', true,  true ],
  ];
  const hs = 2.2; // ハンドルの半サイズ（SVG単位）
  handles.forEach(([hid, hx, hy, cursor]) => {
    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('x', hx - hs); rect.setAttribute('y', hy - hs);
    rect.setAttribute('width', hs * 2); rect.setAttribute('height', hs * 2);
    rect.setAttribute('fill', 'white');
    rect.setAttribute('stroke', '#c00');
    rect.setAttribute('stroke-width', '0.6');
    rect.style.cursor = cursor;
    rect.style.pointerEvents = 'auto';
    rect.dataset.handle = hid;
    rect.addEventListener('mousedown', e => startHandleDrag(e, hid));
    g.appendChild(rect);
  });

  canvas.appendChild(g);
}

// ハンドルドラッグ
function startHandleDrag(e, hid) {
  e.preventDefault(); e.stopPropagation();
  e.target.setPointerCapture(e.pointerId);
  if (!selFrameBBox) return;
  const p = svgPoint(e);
  handleDrag = {
    handle: hid,
    startP: p,
    bbox: { ...selFrameBBox },
    baseScales: new Map(selectionBaseScales),
  };
  document.addEventListener('mousemove', onHandleDrag);
  document.addEventListener('mouseup', endHandleDrag);
}

function onHandleDrag(e) {
  if (!handleDrag) return;
  const p = svgPoint(e);
  const { handle, startP, bbox, baseScales } = handleDrag;
  const dx = p.x - startP.x;
  const dy = p.y - startP.y;
  const MIN = 0.05;

  // ハンドル種別ごとにスケール係数を計算
  let fx = 1, fy = 1;
  switch (handle) {
    case 'mr': fx = Math.max(MIN, (bbox.w + dx) / bbox.w); break;
    case 'ml': fx = Math.max(MIN, (bbox.w - dx) / bbox.w); break;
    case 'bm': fy = Math.max(MIN, (bbox.h + dy) / bbox.h); break;
    case 'tm': fy = Math.max(MIN, (bbox.h - dy) / bbox.h); break;
    case 'br': fx = Math.max(MIN, (bbox.w + dx) / bbox.w);
               fy = Math.max(MIN, (bbox.h + dy) / bbox.h); break;
    case 'bl': fx = Math.max(MIN, (bbox.w - dx) / bbox.w);
               fy = Math.max(MIN, (bbox.h + dy) / bbox.h); break;
    case 'tr': fx = Math.max(MIN, (bbox.w + dx) / bbox.w);
               fy = Math.max(MIN, (bbox.h - dy) / bbox.h); break;
    case 'tl': fx = Math.max(MIN, (bbox.w - dx) / bbox.w);
               fy = Math.max(MIN, (bbox.h - dy) / bbox.h); break;
  }

  // ハンドルの反対側がアンカー（動かない基点）
  const { minX, minY, maxX, maxY, w, h } = bbox;
  const midX = minX + w / 2, midY = minY + h / 2;
  let anchorX, anchorY;
  switch (handle) {
    case 'mr': anchorX = minX; anchorY = midY; break;
    case 'ml': anchorX = maxX; anchorY = midY; break;
    case 'bm': anchorX = midX; anchorY = minY; break;
    case 'tm': anchorX = midX; anchorY = maxY; break;
    case 'br': anchorX = minX; anchorY = minY; break;
    case 'bl': anchorX = maxX; anchorY = minY; break;
    case 'tr': anchorX = minX; anchorY = maxY; break;
    case 'tl': anchorX = maxX; anchorY = maxY; break;
  }

  // スケール＋位置を一体で更新（グループ全体を一つとして拡縮）
  for (const [instId, base] of baseScales) {
    const inst = placedKanji.find(k => k.id === instId);
    if (!inst) continue;
    inst.scaleX = +(base.scaleX * fx).toFixed(4);
    inst.scaleY = +(base.scaleY * fy).toFixed(4);
    // アンカー基準で視覚的な原点位置をスケールに合わせて移動
    inst.tx = +(anchorX + fx * (base.tx + inst.cx - anchorX) - inst.cx).toFixed(4);
    inst.ty = +(anchorY + fy * (base.ty + inst.cy - anchorY) - inst.cy).toFixed(4);
    updateTransform(inst);
    if (inst.id === activeId) syncSliders(inst);
  }

  // フレーム再描画
  renderSelectionFrame();
}

function endHandleDrag() {
  if (handleDrag) pushHistory();
  handleDrag = null;
  document.removeEventListener('mousemove', onHandleDrag);
  document.removeEventListener('mouseup', endHandleDrag);
}

function makeTransform(inst) {
  const sx = +(inst.scale * inst.scaleX).toFixed(4);
  const sy = +(inst.scale * inst.scaleY).toFixed(4);
  return [
    `translate(${inst.tx + inst.cx}, ${inst.ty + inst.cy})`,
    `rotate(${inst.rotate})`,
    `scale(${sx}, ${sy})`,
    `translate(${-inst.cx}, ${-inst.cy})`,
  ].join(' ');
}

// 各筆画をローカル座標の重心に基づいてスプレッド
function applySpread(g, inst) {
  if (!inst.spreadX && !inst.spreadY) return;
  g.querySelectorAll('path').forEach(p => {
    const bb = p.getBBox();
    const pcx = bb.x + bb.width  / 2;
    const pcy = bb.y + bb.height / 2;
    const dx = inst.spreadX ? Math.sign(pcx - inst.cx) * inst.spreadX : 0;
    const dy = inst.spreadY ? Math.sign(pcy - inst.cy) * inst.spreadY : 0;
    if (!dx && !dy) return;
    const existing = p.getAttribute('transform');
    p.setAttribute('transform', existing
      ? `translate(${dx.toFixed(2)},${dy.toFixed(2)}) ${existing}`
      : `translate(${dx.toFixed(2)},${dy.toFixed(2)})`);
  });
}

// ===== アクティブ管理 =====
function setActive(id) {
  activeId = id;
  renderCanvas();
  if (markedStrokes.size > 0) requestAnimationFrame(renderSelectionFrame);
  const inst = placedKanji.find(k => k.id === id);
  if (inst) {
    noActive.style.display = 'none';
    activePanel.style.display = 'block';
    activeTitle.textContent = inst.char;
    activeTitle.style.color = inst.color;
    syncSliders(inst);
    renderStrokeList(inst);
  } else {
    noActive.style.display = 'block';
    activePanel.style.display = 'none';
  }
}

function syncSliders(inst) {
  slX.value  = inst.tx;
  slY.value  = inst.ty;
  slR.value  = inst.rotate;
  slS.value  = inst.scale;
  slSX.value = inst.scaleX;
  slSY.value = inst.scaleY;
  valX.textContent  = inst.tx.toFixed(1);
  valY.textContent  = inst.ty.toFixed(1);
  valR.textContent  = inst.rotate + '°';
  valS.textContent  = inst.scale.toFixed(2);
  valSX.textContent = inst.scaleX.toFixed(2);
  valSY.textContent = inst.scaleY.toFixed(2);
  document.getElementById('sl-spx').value = inst.spreadX ?? 0;
  document.getElementById('sl-spy').value = inst.spreadY ?? 0;
  document.getElementById('val-spx').textContent = (inst.spreadX ?? 0).toFixed(1);
  document.getElementById('val-spy').textContent = (inst.spreadY ?? 0).toFixed(1);
}

function getActive() { return placedKanji.find(k => k.id === activeId) ?? null; }

function updateTransform(inst) {
  const g = canvas.querySelector(`.kanji-instance[data-id="${inst.id}"]`);
  if (g) g.setAttribute('transform', makeTransform(inst));
}

// ===== スライダー =====
function bindSlider(sl, val, prop, fmt) {
  sl.addEventListener('input', () => {
    const inst = getActive(); if (!inst) return;
    inst[prop] = +sl.value;
    val.textContent = fmt(inst[prop]);
    updateTransform(inst);
  });
  sl.addEventListener('change', () => { if (getActive()) pushHistory(); });
}
bindSlider(slX,  valX,  'tx',     v => v.toFixed(1));
bindSlider(slY,  valY,  'ty',     v => v.toFixed(1));
bindSlider(slR,  valR,  'rotate', v => v + '°');
bindSlider(slS,  valS,  'scale',  v => v.toFixed(2));
bindSlider(slSX, valSX, 'scaleX', v => v.toFixed(2));
bindSlider(slSY, valSY, 'scaleY', v => v.toFixed(2));

// ===== スプレッドスライダー =====
function bindSpreadSlider(slId, valId, prop) {
  const sl  = document.getElementById(slId);
  const val = document.getElementById(valId);
  sl.addEventListener('input', () => {
    const inst = getActive(); if (!inst) return;
    inst[prop] = +sl.value;
    val.textContent = inst[prop].toFixed(1);
    renderCanvas();
    if (inst.id === activeId) {
      setActive(inst.id);
    }
  });
  sl.addEventListener('change', () => { if (getActive()) pushHistory(); });
}
bindSpreadSlider('sl-spx', 'val-spx', 'spreadX');
bindSpreadSlider('sl-spy', 'val-spy', 'spreadY');

// ===== 筆画リスト =====
function renderStrokeList(inst) {
  strokeList.innerHTML = '';
  const kept     = inst.strokes.filter(s => s.op !== 'remove').length;
  const duped    = inst.strokes.filter(s => s.op === 'duplicate').length;
  const removed  = inst.strokes.filter(s => s.op === 'remove').length;
  strokeSummary.textContent =
    `${kept}/${inst.strokes.length}画` +
    (duped   > 0 ? ` ・${duped}複製`   : '') +
    (removed > 0 ? ` ・${removed}省略` : '');

  inst.strokes.forEach(stroke => {
    const row = document.createElement('div');
    row.className = `stroke-row op-${stroke.op}`;

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', '32');
    svg.setAttribute('height', '32');
    svg.setAttribute('viewBox', '0 0 109 109');
    const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    p.setAttribute('d', stroke.d);
    p.setAttribute('fill', 'none');
    p.setAttribute('stroke', stroke.op === 'remove' ? '#ccc' : inst.color);
    p.setAttribute('stroke-width', '5');
    p.setAttribute('stroke-linecap', 'round');
    svg.appendChild(p);
    row.appendChild(svg);

    const label = document.createElement('span');
    label.className = 'stroke-label';
    label.textContent = stroke.index + 1;
    row.appendChild(label);

    const btnGroup = document.createElement('div');
    btnGroup.className = 'op-btns';
    [['keep','表示'],['remove','省略'],['duplicate','複製']].forEach(([op, lbl]) => {
      const btn = document.createElement('button');
      btn.textContent = lbl;
      btn.className = 'btn-op' + (stroke.op === op ? ' active' : '');
      btn.addEventListener('click', () => {
        if (stroke.op === op) return;
        stroke.op = op;
        pushHistory();
        renderCanvas();
        renderStrokeList(inst);
      });
      btnGroup.appendChild(btn);
    });
    row.appendChild(btnGroup);
    strokeList.appendChild(row);
  });
}

// ===== 削除 =====
document.getElementById('btn-remove-kanji').addEventListener('click', () => {
  placedKanji = placedKanji.filter(k => k.id !== activeId);
  activeId = null;
  pushHistory();
  renderCanvas();
  noActive.style.display = 'block';
  activePanel.style.display = 'none';
});

// キャンバス背景クリック（範囲選択後でない場合のみ解除）
canvas.addEventListener('click', () => {
  if (rectDidDrag) return; // 範囲選択ドラッグ後のクリックは無視
  activeId = null;
  markedStrokes.clear();
  renderCanvas();
  updateSelectionBar();
  noActive.style.display = 'block';
  activePanel.style.display = 'none';
});

// ===== ドラッグ（漢字移動） =====
let drag = null;

function svgPoint(e) {
  const pt = canvas.createSVGPoint();
  pt.x = e.clientX; pt.y = e.clientY;
  return pt.matrixTransform(canvas.getScreenCTM().inverse());
}

function startDrag(e, id) {
  e.preventDefault(); e.stopPropagation();
  e.target.setPointerCapture(e.pointerId);
  setActive(id);
  const inst = placedKanji.find(k => k.id === id);
  const p = svgPoint(e);
  drag = { id, ox: p.x - inst.tx, oy: p.y - inst.ty };
  document.body.style.cursor = 'grabbing';
  document.addEventListener('mousemove', onDrag);
  document.addEventListener('mouseup', endDrag);
}

function onDrag(e) {
  if (!drag) return;
  const inst = placedKanji.find(k => k.id === drag.id);
  if (!inst) return;
  const p = svgPoint(e);
  inst.tx = p.x - drag.ox;
  inst.ty = p.y - drag.oy;
  updateTransform(inst);
  if (inst.id === activeId) syncSliders(inst);
}

function endDrag() {
  if (drag) pushHistory();
  drag = null;
  document.body.style.cursor = '';
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', endDrag);
}

// ===== 範囲選択 =====
let rectSel      = null;  // {x1,y1,x2,y2} in clientX/Y
let rectDidDrag  = false;
const selRectEl  = document.getElementById('sel-rect');

// キャンバス背景のmousedown → 範囲選択開始
canvas.addEventListener('mousedown', e => {
  // 漢字グループ上のクリックは startDrag が処理するので除外
  if (e.target.closest('.kanji-instance')) return;
  rectDidDrag = false;
  rectSel = { x1: e.clientX, y1: e.clientY, x2: e.clientX, y2: e.clientY };
  document.addEventListener('mousemove', onRectDrag);
  document.addEventListener('mouseup', endRectSelect);
});

function onRectDrag(e) {
  if (!rectSel) return;
  rectSel.x2 = e.clientX;
  rectSel.y2 = e.clientY;
  const w = Math.abs(rectSel.x2 - rectSel.x1);
  const h = Math.abs(rectSel.y2 - rectSel.y1);
  if (w > 4 || h > 4) {
    rectDidDrag = true;
    const left   = Math.min(rectSel.x1, rectSel.x2);
    const top    = Math.min(rectSel.y1, rectSel.y2);
    selRectEl.style.cssText = `display:block;left:${left}px;top:${top}px;width:${w}px;height:${h}px`;
  }
}

function endRectSelect() {
  document.removeEventListener('mousemove', onRectDrag);
  document.removeEventListener('mouseup', endRectSelect);
  selRectEl.style.display = 'none';

  if (!rectDidDrag || !rectSel) { rectSel = null; return; }

  const selLeft   = Math.min(rectSel.x1, rectSel.x2);
  const selRight  = Math.max(rectSel.x1, rectSel.x2);
  const selTop    = Math.min(rectSel.y1, rectSel.y2);
  const selBottom = Math.max(rectSel.y1, rectSel.y2);
  rectSel = null;

  // 各筆画パスのスクリーン矩形と交差チェック（一画単位）
  markedStrokes.clear();
  activeId = null;
  canvas.querySelectorAll('.stroke-path').forEach(path => {
    const r = path.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return; // 非表示パスは除外
    const hit = !(r.right < selLeft || r.left > selRight ||
                  r.bottom < selTop  || r.top  > selBottom);
    if (hit) markedStrokes.add(`${path.dataset.instId}:${path.dataset.strokeIdx}`);
  });

  // 選択されたストロークの親インスタンスの現在スケールを保存
  selectionBaseScales.clear();
  for (const key of markedStrokes) {
    const instId = +key.split(':')[0];
    const inst = placedKanji.find(k => k.id === instId);
    if (inst && !selectionBaseScales.has(instId)) {
      selectionBaseScales.set(instId, {
        scale: inst.scale, scaleX: inst.scaleX, scaleY: inst.scaleY,
        tx: inst.tx, ty: inst.ty,
      });
    }
  }
  renderCanvas();
  updateSelectionBar();
  if (markedStrokes.size > 0) {
    noActive.style.display = 'block';
    activePanel.style.display = 'none';
    requestAnimationFrame(renderSelectionFrame);
  }
}

function updateSelectionBar() {
  const bar   = document.getElementById('selection-bar');
  const count = document.getElementById('selection-count');
  if (markedStrokes.size > 0) {
    bar.style.display = 'flex';
    count.textContent = `${markedStrokes.size}画選択中`;
  } else {
    bar.style.display = 'none';
  }
}

document.getElementById('btn-delete-selection').addEventListener('click', () => {
  // マークされた筆画を op:'remove' に設定
  for (const key of markedStrokes) {
    const [instId, strokeIdx] = key.split(':').map(Number);
    const inst = placedKanji.find(k => k.id === instId);
    if (!inst) continue;
    const stroke = inst.strokes.find(s => s.index === strokeIdx);
    if (stroke) stroke.op = 'remove';
  }
  markedStrokes.clear();
  selectionBaseScales.clear();
  pushHistory();
  renderCanvas();
  updateSelectionBar();
  const active = getActive();
  if (active) renderStrokeList(active);
});

document.getElementById('btn-clear-selection').addEventListener('click', () => {
  markedStrokes.clear();
  selectionBaseScales.clear();
  renderCanvas(); // renderCanvas内でremoveSelectionFrameが呼ばれる
  updateSelectionBar();
});

// ===== AI生成 =====
async function fetchKanjiData(code) {
  const res = await fetch(`/data/kanjivg/kanji_${code}.svg`);
  if (!res.ok) throw new Error(`kanji_${code}.svg not found`);
  const text = await res.text();
  const data = parseKanjiSVG(text);
  data.char = String.fromCodePoint(parseInt(code, 16));
  data.code = code;
  return data;
}

// ===== MLX サーバー自動管理 =====
let mlxStopTimer = null

function resetMlxStopTimer() {
  if (mlxStopTimer) clearTimeout(mlxStopTimer)
  // 5分間AI提案が使われなければ自動停止
  mlxStopTimer = setTimeout(async () => {
    await fetch('/api/mlx-stop', { method: 'POST' })
    document.getElementById('btn-generate').textContent = 'AI提案'
  }, 5 * 60 * 1000)
}

async function ensureMlxRunning(statusEl) {
  // すでに起動中なら即返す
  const check = await fetch('/api/mlx-status').then(r => r.json()).catch(() => ({ running: false }))
  if (check.running) return true

  // 起動開始
  statusEl.textContent = 'モデル起動中…（初回は30秒ほどかかります）'
  statusEl.style.color = '#888'
  await fetch('/api/mlx-start', { method: 'POST' })

  // 最大60秒ポーリング
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 1000))
    const st = await fetch('/api/mlx-status').then(r => r.json()).catch(() => ({ running: false }))
    if (st.running) return true
    statusEl.textContent = `モデル起動中… ${i + 1}秒`
  }
  return false
}

document.getElementById('btn-generate').addEventListener('click', async () => {
  if (!currentTheme) {
    saveStatus.textContent = 'お題を選んでください';
    saveStatus.style.color = '#c00';
    setTimeout(() => { saveStatus.textContent = ''; }, 2000);
    return;
  }
  const btn = document.getElementById('btn-generate');
  btn.disabled = true;
  btn.textContent = '起動中…';
  saveStatus.textContent = '';

  // MLXサーバーが止まっていれば起動
  const ready = await ensureMlxRunning(saveStatus)
  if (!ready) {
    saveStatus.textContent = 'モデルの起動に失敗しました';
    saveStatus.style.color = '#c00';
    btn.disabled = false;
    btn.textContent = 'AI提案';
    return;
  }

  btn.textContent = '生成中…';
  saveStatus.textContent = '';
  resetMlxStopTimer(); // 使用ごとにタイマーリセット

  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ theme: currentTheme }),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    // キャンバスをクリアして生成結果を配置
    placedKanji = [];
    activeId = null;
    markedStrokes.clear();
    selectionBaseScales.clear();
    nextId = 0;

    for (const inst of data.instances) {
      const code = inst.code?.toLowerCase().padStart(5, '0');
      let kData;
      try { kData = await fetchKanjiData(code); }
      catch { console.warn('スキップ:', inst.char, code); continue; }

      const { cx, cy } = getKanjiCenter(kData.paths);
      const t = inst.transform || {};
      const removed = new Set(inst.removedIndices || []);
      placedKanji.push({
        id: nextId++,
        char: kData.char,
        code: kData.code,
        color: INSTANCE_COLORS[(nextId - 1) % INSTANCE_COLORS.length],
        tx: t.tx ?? 0, ty: t.ty ?? 0,
        rotate: t.rotate ?? 0,
        scale: t.scale ?? 1,
        scaleX: t.scaleX ?? 1,
        scaleY: t.scaleY ?? 1,
        spreadX: t.spreadX ?? 0,
        spreadY: t.spreadY ?? 0,
        cx, cy,
        strokes: kData.paths.map((p, i) => ({
          index: i, d: p.d, op: removed.has(i) ? 'remove' : 'keep',
        })),
      });
    }

    pushHistory();
    renderCanvas();
    noActive.style.display = 'block';
    activePanel.style.display = 'none';

    // AI生成直後の状態を記録（後で差分計算に使う）
    aiSnapshot = {
      theme: currentTheme,
      symbol_id: null, // 自動保存後に設定
      interpretation: data.interpretation || null,
      instances: placedKanji.map(inst => ({
        char: inst.char,
        code: inst.code,
        removedIndices: inst.strokes.filter(s => s.op === 'remove').map(s => s.index),
        transform: { tx: inst.tx, ty: inst.ty, rotate: inst.rotate,
                     scale: inst.scale, scaleX: inst.scaleX, scaleY: inst.scaleY },
      })),
    };

    // ギャラリーに自動保存（採点用）
    saveStatus.textContent = '生成中… ギャラリーに保存しています';
    saveStatus.style.color = '#228822';
    const autoId = await autoSaveAiProposal();
    if (autoId) {
      aiSnapshot.symbol_id = autoId;
      saveStatus.textContent = 'AI提案をギャラリーに保存しました';
      showAiScorePanel(autoId, aiSnapshot.interpretation);
    } else {
      saveStatus.textContent = '提案を生成しました（保存失敗）';
    }
    saveStatus.style.color = '#228822';
    setTimeout(() => { saveStatus.textContent = ''; }, 2500);
    updateThemeCount();
  } catch (e) {
    saveStatus.textContent = `エラー: ${e.message}`;
    saveStatus.style.color = '#c00';
  } finally {
    btn.disabled = false;
    btn.textContent = 'AI提案';
  }
});

// ===== AI提案の自動保存 =====
async function autoSaveAiProposal() {
  const visible = placedKanji.filter(inst => inst.strokes.some(s => s.op !== 'remove'));
  if (visible.length === 0) return null;

  const centroids    = collectStrokeCentroids();
  const bboxes       = computeInstanceBBoxes();
  const overlapPairs = computeOverlapPairs(bboxes);
  const symbolBBox   = bboxes.length > 0 ? (() => {
    const minX = Math.min(...bboxes.map(b => b.x));
    const minY = Math.min(...bboxes.map(b => b.y));
    const maxX = Math.max(...bboxes.map(b => b.x + b.w));
    const maxY = Math.max(...bboxes.map(b => b.y + b.h));
    return { x: +minX.toFixed(2), y: +minY.toFixed(2),
      w: +(maxX-minX).toFixed(2), h: +(maxY-minY).toFixed(2),
      cx: +((minX+maxX)/2).toFixed(2), cy: +((minY+maxY)/2).toFixed(2) };
  })() : null;

  const instances = placedKanji
    .filter(inst => inst.strokes.some(s => s.op !== 'remove'))
    .map(inst => {
      const removedIdx    = inst.strokes.filter(s => s.op === 'remove').map(s => s.index);
      const duplicatedIdx = inst.strokes.filter(s => s.op === 'duplicate').map(s => s.index);
      const bb = bboxes.find(b => b.instId === inst.id);
      return {
        char: inst.char, code: inst.code,
        ...(bb ? { bbox: { x: bb.x, y: bb.y, w: bb.w, h: bb.h } } : {}),
        transform: {
          tx: +inst.tx.toFixed(2), ty: +inst.ty.toFixed(2),
          rotate: +inst.rotate, scale: +inst.scale.toFixed(3),
          scaleX: +inst.scaleX.toFixed(3), scaleY: +inst.scaleY.toFixed(3),
          cx: +inst.cx.toFixed(2), cy: +inst.cy.toFixed(2),
          ...(inst.spreadX ? { spreadX: +inst.spreadX.toFixed(2) } : {}),
          ...(inst.spreadY ? { spreadY: +inst.spreadY.toFixed(2) } : {}),
        },
        strokes: inst.strokes.map(s => {
          const entry = { index: s.index, op: s.op };
          if (s.op !== 'remove') { const c = centroids.get(`${inst.id}:${s.index}`); if (c) entry.centroid = c; }
          return entry;
        }),
        abstraction: {
          totalStrokes: inst.strokes.length,
          kept:       inst.strokes.filter(s => s.op === 'keep').length,
          removed:    removedIdx.length,
          duplicated: duplicatedIdx.length,
          removedIndices: removedIdx,
          duplicatedIndices: duplicatedIdx,
        },
      };
    });

  const symbolId = crypto.randomUUID();
  const userInterp = document.getElementById('interp-input').value.trim();
  const record = {
    symbol_id:  symbolId,
    session_id: SESSION_ID,
    theme:      currentTheme,
    timestamp:  new Date().toISOString(),
    source:     'ai',
    model_version: 'ft-v1',
    ...(aiSnapshot?.interpretation ? { interpretation: aiSnapshot.interpretation } : {}),
    ...(symbolBBox     ? { symbol_bbox:   symbolBBox }   : {}),
    ...(overlapPairs.length ? { overlap_pairs: overlapPairs } : {}),
    instances,
  };
  try {
    const res  = await fetch('/api/ai-save', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(record),
    });
    const data = await res.json();
    return data.ok ? symbolId : null;
  } catch (_) { return null; }
}

// ===== AI採点パネル =====
let aiScoreSymbolId = null;
let aiScoreState = 'graphic'; // 'graphic' | 'abstraction' | 'confirm'
let aiPendingG = null;
let aiPendingA = null;

function showAiScorePanel(symbolId, interpretation) {
  aiScoreSymbolId = symbolId;
  aiPendingG = null;
  aiPendingA = null;
  aiScoreState = 'graphic';
  document.getElementById('ai-sc-g').value = 5;
  document.getElementById('ai-val-g').textContent = '5';
  document.getElementById('ai-sc-a').value = 5;
  document.getElementById('ai-val-a').textContent = '5';
  document.getElementById('ai-score-status').textContent = '0-9: グラフィック採点';
  document.getElementById('ai-score-panel').style.display = '';
  document.getElementById('ai-comment-section').style.display = '';

  // 解釈テキスト表示
  const interpEl = document.getElementById('ai-interpretation');
  const interpText = document.getElementById('ai-interp-text');
  if (interpretation) {
    interpText.textContent = interpretation;
    interpEl.style.display = '';
  } else {
    interpEl.style.display = 'none';
  }
}

function hideAiScorePanel() {
  document.getElementById('ai-score-panel').style.display = 'none';
  document.getElementById('ai-interpretation').style.display = 'none';
  const commentSection = document.getElementById('ai-comment-section');
  commentSection.style.display = 'none';
  document.getElementById('ai-comment-input').value = '';
  aiScoreSymbolId = null;
  aiScoreState = 'graphic';
  aiPendingG = null;
  aiPendingA = null;
}

async function submitAiScore(g, a) {
  if (!aiScoreSymbolId) return;
  try {
    const res = await fetch('/api/score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol_id: aiScoreSymbolId, graphic: g, abstraction: a }),
    });
    const data = await res.json();
    if (data.ok) {
      document.getElementById('ai-score-status').textContent = `✓ G${g} A${a} 保存しました`;
      setTimeout(hideAiScorePanel, 1500);
    }
  } catch (_) {
    document.getElementById('ai-score-status').textContent = '保存失敗';
  }
}

document.getElementById('ai-sc-g').addEventListener('input', e => {
  document.getElementById('ai-val-g').textContent = e.target.value;
});
document.getElementById('ai-sc-a').addEventListener('input', e => {
  document.getElementById('ai-val-a').textContent = e.target.value;
});
document.getElementById('btn-score-ai').addEventListener('click', () => {
  const g = +document.getElementById('ai-sc-g').value;
  const a = +document.getElementById('ai-sc-a').value;
  submitAiScore(g, a);
});

// キーボード採点（入力フィールドにフォーカスがない時のみ）
document.addEventListener('keydown', e => {
  const panel = document.getElementById('ai-score-panel');
  if (panel.style.display === 'none') return;
  const tag = document.activeElement?.tagName;
  if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return;

  if (/^[0-9]$/.test(e.key)) {
    const n = +e.key;
    if (aiScoreState === 'graphic') {
      aiPendingG = n;
      document.getElementById('ai-sc-g').value = n;
      document.getElementById('ai-val-g').textContent = n;
      aiScoreState = 'abstraction';
      document.getElementById('ai-score-status').textContent = `G${n} → 0-9: 抽象化採点`;
    } else if (aiScoreState === 'abstraction' || aiScoreState === 'confirm') {
      aiPendingA = n;
      document.getElementById('ai-sc-a').value = n;
      document.getElementById('ai-val-a').textContent = n;
      aiScoreState = 'confirm';
      document.getElementById('ai-score-status').textContent = `G${aiPendingG} A${n} → Enter: 確定`;
    }
    return;
  }

  if (e.key === 'Enter' && aiScoreState === 'confirm') {
    e.preventDefault();
    submitAiScore(aiPendingG, aiPendingA);
    return;
  }

  if (e.key === 'Backspace') {
    if (aiScoreState === 'confirm' || aiScoreState === 'abstraction') {
      aiPendingA = null;
      aiScoreState = 'abstraction';
      document.getElementById('ai-score-status').textContent = `G${aiPendingG} → 0-9: 抽象化採点`;
    }
    return;
  }

  if (e.key === 'Escape') hideAiScorePanel();
});

// ===== サンプル数表示 =====
async function updateThemeCount() {
  const el = document.getElementById('theme-count');
  if (!currentTheme) { el.style.display = 'none'; return; }
  try {
    const res = await fetch(`/api/count?theme=${encodeURIComponent(currentTheme)}`);
    const data = await res.json();
    el.textContent = `${data.count}件`;
    el.style.display = '';
  } catch { el.style.display = 'none'; }
}

// ===== インスタンスのcanvas座標系bboxを計算 =====
function computeInstanceBBoxes() {
  const canvasR = canvas.getBoundingClientRect();
  const sx = 109 / canvasR.width;
  const sy = 109 / canvasR.height;
  const result = [];
  for (const inst of placedKanji) {
    if (!inst.strokes.some(s => s.op !== 'remove')) continue;
    const g = canvas.querySelector(`.kanji-instance[data-id="${inst.id}"]`);
    if (!g) continue;
    try {
      const r = g.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) continue;
      result.push({
        instId: inst.id,
        char: inst.char,
        x: +((r.left - canvasR.left) * sx).toFixed(2),
        y: +((r.top  - canvasR.top)  * sy).toFixed(2),
        w: +(r.width  * sx).toFixed(2),
        h: +(r.height * sy).toFixed(2),
      });
    } catch (_) {}
  }
  return result;
}

// ===== インスタンス間の重なり率（IoU）を計算 =====
function computeOverlapPairs(bboxes) {
  const pairs = [];
  for (let i = 0; i < bboxes.length; i++) {
    for (let j = i + 1; j < bboxes.length; j++) {
      const a = bboxes[i], b = bboxes[j];
      const ix = Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x));
      const iy = Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y));
      const inter = ix * iy;
      if (inter <= 0) continue;
      const union = a.w * a.h + b.w * b.h - inter;
      const iou = union > 0 ? +(inter / union).toFixed(3) : 0;
      if (iou > 0) pairs.push({ chars: [a.char, b.char], iou });
    }
  }
  return pairs;
}

// ===== 各筆画の重心（SVG座標）を取得 =====
function collectStrokeCentroids() {
  const map = new Map(); // "instId:strokeIdx" → {x, y}
  canvas.querySelectorAll('.stroke-path').forEach(path => {
    const key = `${path.dataset.instId}:${path.dataset.strokeIdx}`;
    const r = path.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    const p = clientToSVG((r.left + r.right) / 2, (r.top + r.bottom) / 2);
    map.set(key, { x: +p.x.toFixed(2), y: +p.y.toFixed(2) });
  });
  return map;
}

// ===== 保存 =====
document.getElementById('btn-save').addEventListener('click', async () => {
  // 空白チェック
  const visible = placedKanji.filter(inst => inst.strokes.some(s => s.op !== 'remove'));
  if (visible.length === 0) {
    saveStatus.textContent = '漢字を配置してください';
    saveStatus.style.color = '#c00';
    setTimeout(() => { saveStatus.textContent = ''; }, 2000);
    return;
  }

  const centroids = collectStrokeCentroids();
  const bboxes    = computeInstanceBBoxes();
  const overlapPairs = computeOverlapPairs(bboxes);

  // 記号全体のフットプリント（省略後の kept strokes の合算領域）
  const symbolBBox = bboxes.length > 0 ? (() => {
    const minX = Math.min(...bboxes.map(b => b.x));
    const minY = Math.min(...bboxes.map(b => b.y));
    const maxX = Math.max(...bboxes.map(b => b.x + b.w));
    const maxY = Math.max(...bboxes.map(b => b.y + b.h));
    return {
      x:  +minX.toFixed(2),
      y:  +minY.toFixed(2),
      w:  +(maxX - minX).toFixed(2),
      h:  +(maxY - minY).toFixed(2),
      cx: +((minX + maxX) / 2).toFixed(2),
      cy: +((minY + maxY) / 2).toFixed(2),
    };
  })() : null;

  const instances = placedKanji
    .filter(inst => inst.strokes.some(s => s.op !== 'remove'))
    .map(inst => {
      const removedIdx    = inst.strokes.filter(s => s.op === 'remove').map(s => s.index);
      const duplicatedIdx = inst.strokes.filter(s => s.op === 'duplicate').map(s => s.index);
      const bb = bboxes.find(b => b.instId === inst.id);
      return {
        char: inst.char,
        code: inst.code,
        ...(bb ? { bbox: { x: bb.x, y: bb.y, w: bb.w, h: bb.h } } : {}),
        transform: {
          tx: +inst.tx.toFixed(2),
          ty: +inst.ty.toFixed(2),
          rotate: +inst.rotate,
          scale:  +inst.scale.toFixed(3),
          scaleX: +inst.scaleX.toFixed(3),
          scaleY: +inst.scaleY.toFixed(3),
          cx: +inst.cx.toFixed(2),
          cy: +inst.cy.toFixed(2),
          ...(inst.spreadX ? { spreadX: +inst.spreadX.toFixed(2) } : {}),
          ...(inst.spreadY ? { spreadY: +inst.spreadY.toFixed(2) } : {}),
        },
        strokes: inst.strokes.map(s => {
          const entry = { index: s.index, op: s.op };
          if (s.op !== 'remove') {
            const c = centroids.get(`${inst.id}:${s.index}`);
            if (c) entry.centroid = c;
          }
          return entry;
        }),
        abstraction: {
          totalStrokes: inst.strokes.length,
          kept:       inst.strokes.filter(s => s.op === 'keep').length,
          removed:    removedIdx.length,
          duplicated: duplicatedIdx.length,
          removedIndices:    removedIdx,
          duplicatedIndices: duplicatedIdx,
        },
      };
    });

  const symbolId = crypto.randomUUID();
  const userInterp = document.getElementById('interp-input').value.trim();

  // ===== AI生成からの差分を計算 =====
  let aiEditInfo = null;
  if (aiSnapshot && aiSnapshot.theme === currentTheme) {
    const origByCode  = new Map(aiSnapshot.instances.map(i => [i.code, i]));
    const finalByCode = new Map(instances.map(i => [i.code, i]));

    const kanji_removed = aiSnapshot.instances
      .filter(i => !finalByCode.has(i.code)).map(i => i.char);
    const kanji_added = instances
      .filter(i => !origByCode.has(i.code)).map(i => i.char);
    const kanji_modified = [];

    for (const [code, orig] of origByCode) {
      const fin = finalByCode.get(code);
      if (!fin) continue;
      const tDiff = {};
      for (const k of ['tx','ty','rotate','scale','scaleX','scaleY']) {
        if (Math.abs((orig.transform[k] ?? 1) - (fin.transform[k] ?? 1)) > 0.01)
          tDiff[k] = { from: orig.transform[k], to: fin.transform[k] };
      }
      const origRemoved = new Set(orig.removedIndices);
      const finRemoved  = new Set(fin.strokes.filter(s => s.op === 'remove').map(s => s.index));
      const strokesAdded   = [...finRemoved].filter(i => !origRemoved.has(i));   // 新たに省略
      const strokesRestored= [...origRemoved].filter(i => !finRemoved.has(i));   // 省略を復元
      if (Object.keys(tDiff).length || strokesAdded.length || strokesRestored.length) {
        kanji_modified.push({
          char: orig.char,
          ...(Object.keys(tDiff).length ? { transform_changed: tDiff } : {}),
          ...(strokesAdded.length   ? { strokes_removed_added: strokesAdded }   : {}),
          ...(strokesRestored.length? { strokes_removal_undone: strokesRestored }: {}),
        });
      }
    }
    aiEditInfo = {
      ai_original: aiSnapshot.instances,
      kanji_removed,
      kanji_added,
      kanji_modified,
    };
  }

  const isAiRecord = aiSnapshot !== null && aiSnapshot.theme === currentTheme;
  const hasEdits = aiEditInfo && (
    aiEditInfo.kanji_removed.length > 0 ||
    aiEditInfo.kanji_added.length > 0 ||
    aiEditInfo.kanji_modified.length > 0
  );
  const source = isAiRecord ? (hasEdits ? 'hybrid' : 'ai') : 'human';

  const aiComment = document.getElementById('ai-comment-input').value.trim();

  const record = {
    symbol_id:      symbolId,
    prev_symbol_id: lastSymbolId,
    session_id:     SESSION_ID,
    theme:          currentTheme,
    timestamp:      new Date().toISOString(),
    source,
    ...(isAiRecord ? { model_version: 'ft-v1' } : {}),
    ...(userInterp ? { interpretation: userInterp } : (aiSnapshot?.interpretation ? { interpretation: aiSnapshot.interpretation } : {})),
    ...(symbolBBox   ? { symbol_bbox: symbolBBox }     : {}),
    ...(overlapPairs.length ? { overlap_pairs: overlapPairs } : {}),
    ...(aiEditInfo ? { ai_edit: aiEditInfo } : {}),
    ...(source === 'hybrid' && aiComment ? { ai_comment: aiComment } : {}),
    instances,
  };

  // AI提案が自動保存済みで変更なし → 再保存しない
  if (source === 'ai' && aiSnapshot.symbol_id) {
    lastSymbolId = aiSnapshot.symbol_id;
    aiSnapshot = null;
    showSaveOverlay(record);
    return;
  }

  const saveEndpoint = source === 'hybrid' ? '/api/hybrid-save' : '/api/save';

  try {
    const res = await fetch(saveEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(record),
    });
    const data = await res.json();
    if (data.ok) {
      lastSymbolId = symbolId;
      aiSnapshot = null; // 保存完了でリセット
      document.getElementById('interp-input').value = '';
      hideAiScorePanel();
      showSaveOverlay(record);
      updateThemeCount();
    } else {
      saveStatus.textContent = '保存失敗';
      saveStatus.style.color = '#c00';
      setTimeout(() => { saveStatus.textContent = ''; }, 3000);
    }
  } catch (err) {
    saveStatus.textContent = `エラー: ${err.message}`;
    saveStatus.style.color = '#c00';
  }
});

// ===== 保存オーバーレイ =====
function showSaveOverlay(record) {
  const overlay = document.getElementById('save-overlay');
  const totalStrokes = record.instances.reduce(
    (sum, inst) => sum + inst.abstraction.kept, 0
  );
  const chars = record.instances.map(i => i.char).join('・');

  document.getElementById('overlay-theme').textContent =
    record.theme || '（テーマなし）';
  document.getElementById('overlay-detail').textContent =
    `${chars}　${totalStrokes}画`;

  overlay.classList.remove('show');
  // リフロー強制してアニメーションをリセット
  void overlay.offsetWidth;
  overlay.classList.add('show');
}

document.getElementById('save-overlay').addEventListener('click', () => {
  document.getElementById('save-overlay').classList.remove('show');
});

// ===== Undo/Redo =====
document.getElementById('btn-undo').addEventListener('click', undo);
document.getElementById('btn-redo').addEventListener('click', redo);
document.addEventListener('keydown', e => {
  // テキスト入力中は無視
  if (e.target.matches('input, textarea')) return;

  // Delete / Backspace → 範囲選択中の筆画を省略
  if ((e.key === 'Delete' || e.key === 'Backspace') && markedStrokes.size > 0) {
    e.preventDefault();
    document.getElementById('btn-delete-selection').click();
    return;
  }

  const mod = e.metaKey || e.ctrlKey;
  if (!mod) return;
  if (e.key === 'z' && !e.shiftKey) { e.preventDefault(); undo(); }
  if (e.key === 'z' &&  e.shiftKey) { e.preventDefault(); redo(); }
  if (e.key === 'y')                { e.preventDefault(); redo(); }
});

// ===== 初期化 =====
currentTheme = THEMES[Math.floor(Math.random() * THEMES.length)];
themeText.textContent = currentTheme;
loadKanji(selectedCode);
syncHistoryBtns();
initKanjiList();
