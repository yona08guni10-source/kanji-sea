#!/usr/bin/env python3
"""
prepare_finetune.py — IDS Symbol Renderer fine-tuning data builder (v3)

5種類の学習形式を生成:
  A: お題 → 考察 + JSON生成（メイン）
  B: 記号JSON → 構造と意味の解説（interpretationのある記録から）
  C: 構造パターン名 → 説明と事例（研究パターンから）
  D: 創作哲学・漢字選択についての問答
  E: ChainOfThought — 特殊トークンを使った思考過程付き生成

品質重み付け: G+A >= 14 の記録は Format A を 3x 重複

出力: finetune_data/train.jsonl, finetune_data/valid.jsonl
"""

import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / "finetune_data"
DATA_DIR.mkdir(exist_ok=True)

QUALITY_THRESHOLD  = 10  # AI/hybrid の G+A 最低スコア
HIGH_QUALITY_MIN   = 14  # Format A を 3x 重複させる G+A 閾値
COT_INTERP_MIN_LEN = 20  # Format E を生成するための最低 interpretation 文字数
CANVAS_CENTER      = 54.5  # キャンバスサイズ 109px の中心

# ─── 構造タグの日本語名 ────────────────────────────────────────────────────────
TAG_LABELS = {
    "single_heavy_removal":           "単漢字・大量除去",
    "single_partial_removal":         "単漢字・部分除去",
    "single_intact":                  "単漢字・原形保持",
    "dual_overlap":                   "二字重畳",
    "dual_horizontal":                "二字横並び",
    "dual_vertical":                  "二字縦積み",
    "dual_diagonal":                  "二字斜め配置",
    "dual_complementary_horizontal":  "二字相補（横）",
    "dual_complementary_vertical":    "二字相補（縦）",
    "repeated_overlap":               "同字重畳",
    "repeated_horizontal":            "同字横並び",
    "repeated_vertical":              "同字縦積み",
    "triple_composition":             "三字組み合わせ",
    "triple_repeated":                "三字反復",
    "multi_kanji":                    "多漢字複合",
}

# ─── システムプロンプト ────────────────────────────────────────────────────────
SYSTEM_PROMPT = """あなたは漢字の筆画を組み合わせて抽象的な記号を生成・解説する専門家AIです。

## キャンバス仕様
- 109×109 SVG座標系、中心(0, 0)基準
- tx/ty: 中心からの位置オフセット（正：右/下、負：左/上）
- scaleX/scaleY: 水平/垂直方向の拡縮（1.0=原寸）
- rotate: 回転角度（度）
- removedIndices: 省略する筆画のインデックスリスト（0始まり）

## 記号の構造タイプ
- 単漢字・大量除去: 1字から核心的な筆画だけを残す（除去率60%以上）
- 二字重畳: 2つの漢字を重ねて融合させる
- 二字相補: 2つの漢字が互いに補い合う筆画を担当（一方が前半、他方が後半）
- 二字横並び/縦積み: 左右または上下に分割配置
- 三字組み合わせ: 3つの漢字で空間的な関係性を構成
- 同字反復: 同じ漢字を変形・移動させて重ねるまたは並べる
- 多漢字複合: 4字以上の複合構造

## 制作データの読み方
- [手作り] = 作者が直接制作した高品質な作品
- [AI修正] = AI提案を作者が修正した作品
- [G数字 A数字] = グラフィック採点/抽象化採点（各0-9点）
- 解釈 = その記号を制作した理由・意図"""

# ─── データ読み込み ────────────────────────────────────────────────────────────

def load_jsonl(path):
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def load_scores():
    p = ROOT / "scores.json"
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_research():
    p = ROOT / "research" / "patterns.json"
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def get_trash_keys():
    keys = set()
    for r in load_jsonl(ROOT / "trash.jsonl"):
        k = r.get("symbol_id") or r.get("timestamp")
        if k:
            keys.add(k)
    return keys


def record_key(r):
    return r.get("symbol_id") or r.get("timestamp") or ""


def load_all_quality_records():
    scores     = load_scores()
    trash_keys = get_trash_keys()

    sources = {
        "human":  load_jsonl(ROOT / "results.jsonl"),
        "ai":     load_jsonl(ROOT / "ai_results.jsonl"),
        "hybrid": load_jsonl(ROOT / "hybrid_results.jsonl"),
    }

    records = []
    for source, recs in sources.items():
        for r in recs:
            k = record_key(r)
            if k in trash_keys:
                continue
            r["_source"] = source
            if source in ("human", "hybrid"):
                records.append(r)
            else:  # ai
                s = scores.get(k, {})
                if s.get("graphic", 0) + s.get("abstraction", 0) >= QUALITY_THRESHOLD:
                    records.append(r)
    return records


# ─── インスタンス整形 ──────────────────────────────────────────────────────────

def format_instance(inst):
    ab      = inst.get("abstraction", {})
    removed = ab.get("removedIndices") or \
              [s["index"] for s in inst.get("strokes", []) if s.get("op") == "remove"]
    t = inst.get("transform", {})
    return {
        "char": inst["char"],
        "removedIndices": removed,
        "transform": {
            "tx":     round(t.get("tx",     0), 2),
            "ty":     round(t.get("ty",     0), 2),
            "rotate": round(t.get("rotate", 0), 2),
            "scale":  round(t.get("scale",  1), 3),
            "scaleX": round(t.get("scaleX", 1), 3),
            "scaleY": round(t.get("scaleY", 1), 3),
        },
    }


def format_record_json(record):
    instances = [format_instance(i) for i in record.get("instances", []) if "char" in i]
    if not instances:
        return None
    interp = record.get("interpretation", "").strip()
    return {
        "interpretation": interp or f"お題「{record['theme']}」を漢字の組み合わせで表現した",
        "instances": instances,
    }


def describe_structure(record):
    insts = record.get("instances", [])
    n     = len(insts)
    chars = [i["char"] for i in insts if "char" in i]
    char_counter = Counter(chars)
    unique_chars = list(dict.fromkeys(chars))

    removal_parts = []
    for inst in insts:
        ab    = inst.get("abstraction", {})
        total = ab.get("totalStrokes", 0)
        rem   = ab.get("removed", 0)
        if total > 0:
            removal_parts.append(f"「{inst['char']}」{rem}/{total}画除去")

    if n == 1:
        struct = "単漢字"
    elif n == 2:
        if any(v > 1 for v in char_counter.values()):
            struct = "同字反復"
        else:
            txs = [i.get("transform", {}).get("tx", 0) for i in insts]
            tys = [i.get("transform", {}).get("ty", 0) for i in insts]
            dx  = abs(txs[0] - txs[1]) if len(txs) == 2 else 0
            dy  = abs(tys[0] - tys[1]) if len(tys) == 2 else 0
            dist = (dx**2 + dy**2) ** 0.5
            struct = "二字重畳" if dist < 25 else ("二字横並び" if dx > dy else "二字縦積み")
    elif n == 3:
        struct = "三字組み合わせ"
    else:
        struct = "多漢字複合"

    parts = [f"使用漢字: {'・'.join(unique_chars)}（{struct}）"]
    if removal_parts:
        parts.append("筆画: " + "、".join(removal_parts))
    return "、".join(parts)


# ─── Format A: お題 → 生成 ───────────────────────────────────────────────────

FORMAT_A_USER = """\
お題「{theme}」に対して漢字を選択した理由を述べながら記号を生成してください。

考察を1〜2行述べてからJSONを出力してください:
{{"interpretation":"選択理由を1文で","instances":[{{"char":"漢字","removedIndices":[0,1,2],"transform":{{"tx":0,"ty":0,"rotate":0,"scale":1,"scaleX":1,"scaleY":1}}}}]}}"""

def make_format_a(record):
    out = format_record_json(record)
    if not out:
        return None

    theme  = record.get("theme", "")
    interp = record.get("interpretation", "").strip()

    if interp and len(interp) > 10:
        reasoning = interp
    else:
        chars     = [i["char"] for i in record.get("instances", []) if "char" in i]
        reasoning = f"お題「{theme}」に対して{'・'.join(chars)}の関係性を考察し、記号として構成する。"

    assistant = f"{reasoning}\n{json.dumps(out, ensure_ascii=False)}"

    return {
        "messages": [
            {"role": "system",    "content": SYSTEM_PROMPT},
            {"role": "user",      "content": FORMAT_A_USER.format(theme=theme)},
            {"role": "assistant", "content": assistant},
        ]
    }


# ─── Format B: 記号 → 解説 ───────────────────────────────────────────────────

FORMAT_B_USER = """\
以下の記号の構造と意味を解説してください。

お題: 「{theme}」
記号データ: {json_str}"""

def make_format_b(record):
    interp = record.get("interpretation", "").strip()
    if not interp or len(interp) < 15:
        return None

    out = format_record_json(record)
    if not out:
        return None

    theme  = record.get("theme", "")
    insts  = record.get("instances", [])
    chars  = [i["char"] for i in insts if "char" in i]
    n      = len(insts)
    struct = describe_structure(record)

    if n == 1:
        analysis = f"「{chars[0]}」一字から本質的な筆画だけを残すことで、概念の核心を抽出しています。"
    elif n == 2:
        analysis = (f"「{chars[0]}」と「{chars[1]}」を組み合わせることで、"
                    f"二つの意味が視覚的に融合し、お題「{theme}」の複合的な意味を表現しています。")
    else:
        analysis = (f"{'・'.join(chars)}の{n}字を空間的に配置することで、"
                    f"お題「{theme}」の多層的な意味構造を表現しています。")

    answer = (f"この記号は{struct}で構成されています。\n\n"
              f"{interp}\n\n"
              f"漢字の選択と構造について: {analysis}")

    return {
        "messages": [
            {"role": "system",    "content": SYSTEM_PROMPT},
            {"role": "user",      "content": FORMAT_B_USER.format(
                theme=theme,
                json_str=json.dumps(out, ensure_ascii=False))},
            {"role": "assistant", "content": answer},
        ]
    }


# ─── Format C: 構造パターン問答 ──────────────────────────────────────────────

PATTERN_QUESTIONS = [
    "{name}とはどのような構造ですか？",
    "{name}の制作例を教えてください。",
    "記号制作において{name}はどのような表現効果がありますか？",
]

def make_format_c(pattern, records_by_tag):
    tag       = pattern.get("tag", "")
    # LLM未使用の場合 name が英語タグのままになるため、日本語名を優先
    raw_name  = pattern.get("name", "")
    name      = TAG_LABELS.get(tag) or (raw_name if raw_name != tag else None) or tag
    desc      = pattern.get("description", "")
    effect    = pattern.get("effect", "")
    potential = pattern.get("potential", "")

    samples = records_by_tag.get(tag, [])[:4]
    examples_text = ""
    if samples:
        lines = []
        for r in samples:
            theme  = r.get("theme", "")
            chars  = "・".join(i["char"] for i in r.get("instances", []) if "char" in i)
            interp = r.get("interpretation", "").strip()
            line   = f"・お題「{theme}」：{chars}"
            if interp:
                line += f"（{interp[:35]}）"
            lines.append(line)
        examples_text = "\n\n制作例:\n" + "\n".join(lines)

    jp_name = TAG_LABELS.get(tag, name)
    FALLBACK_DESCS = {
        "single_heavy_removal":          "1つの漢字から60%以上の筆画を除去し、概念の骨格だけを残す構造です。",
        "single_partial_removal":        "1つの漢字から一部の筆画を除去して、元の字の面影を残しながら意味を絞り込む構造です。",
        "single_intact":                 "1つの漢字をほぼ原形のまま使用し、スケールや位置で表現を調整する構造です。",
        "dual_overlap":                  "2つの異なる漢字を重ね合わせ、視覚的に融合させることで新しい意味を生む構造です。",
        "dual_horizontal":               "2つの漢字を左右に並べ、対比・補完・対話の関係を表現する構造です。",
        "dual_vertical":                 "2つの漢字を上下に積み重ね、階層・推移・時間的変化を表現する構造です。",
        "dual_diagonal":                 "2つの漢字を斜めに配置し、動きや方向性のある関係を表現する構造です。",
        "dual_complementary_horizontal": "2つの漢字がそれぞれ異なる筆画グループを担当し、横方向に並んで一つの意味を構成する相補構造です。",
        "dual_complementary_vertical":   "2つの漢字がそれぞれ異なる筆画グループを担当し、縦方向に並んで一つの意味を構成する相補構造です。",
        "repeated_overlap":              "同じ漢字を2つ重ねて配置し、概念の強調・残像・多重性を表現する構造です。",
        "repeated_horizontal":           "同じ漢字を2つ横に並べ、反復・対称・変奏を表現する構造です。",
        "repeated_vertical":             "同じ漢字を2つ縦に積み、変容・継承・対称を表現する構造です。",
        "triple_composition":            "3つの異なる漢字を空間的に配置し、複数の概念の三角的な関係を表現する構造です。",
        "triple_repeated":               "同じ漢字を3つ使用し、三重の反復・増殖・リズムを表現する構造です。",
        "multi_kanji":                   "4字以上の漢字を複合的に組み合わせ、複雑な概念の空間を構築する構造です。",
    }
    fallback = FALLBACK_DESCS.get(tag, f"{jp_name}の構造です。")
    answer = f"{jp_name}は、{desc}" if (desc and tag not in desc) else f"{jp_name}は、{fallback}"
    if effect:
        answer += f"\n\n表現効果: {effect}"
    answer += examples_text
    if potential:
        answer += f"\n\n発展可能性: {potential}"

    return [
        {
            "messages": [
                {"role": "system",    "content": SYSTEM_PROMPT},
                {"role": "user",      "content": q_template.format(name=name)},
                {"role": "assistant", "content": answer},
            ]
        }
        for q_template in PATTERN_QUESTIONS
    ]


# ─── Format D: 創作哲学問答 ──────────────────────────────────────────────────

PHILOSOPHY_QA = [
    (
        "漢字記号を制作するとき、どのような考え方で漢字を選びますか？",
        "漢字選択の核心は「意味の重なり」と「視覚的な形の力」の両立にあります。"
        "お題が持つ概念に最も近い意味を持つ漢字を選びながら、同時にその漢字の筆画構造が"
        "視覚的な印象として概念を体現できるかを考えます。"
        "例えば「覚」と「醒」を組み合わせる場合、「目覚め」という意味の重なりだけでなく、"
        "それぞれの字から特定の筆画群を取り出すことで、覚醒という瞬間の鋭さを表現できます。",
    ),
    (
        "筆画の除去はどのような意図で行いますか？",
        "筆画の除去は「本質の抽出」です。漢字全体が持つ意味の中から、"
        "お題に最も関連する部分だけを残すことで、概念の核心が視覚的に際立ちます。"
        "大量除去（60%以上）は概念の骨格だけを示し、部分除去は元の漢字の面影を残しながら"
        "新しい意味を付与します。除去するインデックスの選択は、"
        "残す筆画が作る「形の意味」を最優先に考えます。",
    ),
    (
        "複数の漢字を組み合わせるとき、配置はどう決めますか？",
        "配置は概念の関係性を空間で表現します。"
        "二字を重ねる（重畳）場合は二つの概念の融合や緊張関係を、"
        "横に並べる場合は対比や補完を、縦に積む場合は階層や時間的な推移を示します。"
        "入れ子構造（一字が他字の視覚的な内側に位置する）は、"
        "包含・潜在・内在という概念を表現するのに有効です。"
        "スケールの差（大きな字と小さな字）は主従関係や遠近感を生みます。",
    ),
    (
        "同じ漢字を複数使う場合、どのような効果がありますか？",
        "同字反復は「変容」「多重性」「エコー」を表現します。"
        "同じ漢字から異なる部分を取り出して並べると、一つの概念の異なる側面が"
        "並立する構造になります。位置を少しずらして重ねると、"
        "概念の揺らぎや残像のような印象を与えます。"
        "スケールを変えて配置すると、同じものが異なる次元に存在するような"
        "多層的な空間を作ることができます。",
    ),
    (
        "抽象度の高い記号と低い記号の違いは何ですか？",
        "抽象度は「元の漢字の認識可能性」で決まります。"
        "筆画を多く除去するほど、または変形が強いほど、"
        "元の漢字が何かは分からなくなりますが純粋な視覚的形として機能します。"
        "高抽象の記号は見る人が自由に意味を読み取れる一方、"
        "低抽象（元の漢字が読める程度）の記号は漢字の意味を知る人に"
        "概念的な理解を与えます。お題の普遍性が高いほど高抽象が有効で、"
        "文化的・知的な文脈が重要なお題は低〜中抽象が効果的です。",
    ),
    (
        "IDS（漢字構造記述）を応用した記号制作とはどういう意味ですか？",
        "IDS（Ideographic Description Sequences）は漢字の部品構造を記述する規格ですが、"
        "この記号制作ではそれを拡張し、漢字の筆画レベルでの分解・再構成を行います。"
        "通常のIDS（左右・上下・囲みなど）に加え、重畳（重ねる）、"
        "相補分割（一方が前半、他方が後半の筆画を担当）、"
        "入れ子（一字の視覚的内側に別字を配置）といった独自の構造も開発されています。"
        "これらは既存のIDS分類では捉えられない新しい文字的空間を創出します。",
    ),
]

def make_format_d():
    return [
        {
            "messages": [
                {"role": "system",    "content": SYSTEM_PROMPT},
                {"role": "user",      "content": q},
                {"role": "assistant", "content": a},
            ]
        }
        for q, a in PHILOSOPHY_QA
    ]


# ─── Format E: ChainOfThought (特殊トークン付き思考過程) ──────────────────────

# IDS 12演算子トークン → 参照基準としての標準配置値
# （109×109 SVG、漢字の実効幅を約50pxと仮定）
IDS_TOKEN_INFO = {
    "<IDS左右>":   {
        "ope": "⿰", "desc": "左右に分割配置",
        "canonical": [{"tx": -27, "ty": 0, "sx": 1.0}, {"tx": 27, "ty": 0, "sx": 1.0}],
    },
    "<IDS上下>":   {
        "ope": "⿱", "desc": "上下に分割配置",
        "canonical": [{"tx": 0, "ty": -25, "sx": 1.0}, {"tx": 0, "ty": 25, "sx": 1.0}],
    },
    "<IDS左中右>": {
        "ope": "⿲", "desc": "左中右の三分割横配置",
        "canonical": [{"tx": -35, "ty": 0, "sx": 0.85}, {"tx": 0, "ty": 0, "sx": 0.85}, {"tx": 35, "ty": 0, "sx": 0.85}],
    },
    "<IDS上中下>": {
        "ope": "⿳", "desc": "上中下の三段縦配置",
        "canonical": [{"tx": 0, "ty": -33, "sx": 0.85}, {"tx": 0, "ty": 0, "sx": 0.85}, {"tx": 0, "ty": 33, "sx": 0.85}],
    },
    "<IDS全囲>":   {"ope": "⿴", "desc": "一字が他字を完全に囲む", "canonical": []},
    "<IDS上囲>":   {"ope": "⿵", "desc": "上方から囲む構造",       "canonical": []},
    "<IDS下囲>":   {"ope": "⿶", "desc": "下方から囲む構造",       "canonical": []},
    "<IDS左囲>":   {"ope": "⿷", "desc": "左方から囲む構造",       "canonical": []},
    "<IDS左上囲>": {"ope": "⿸", "desc": "左上から囲む構造",       "canonical": []},
    "<IDS右上囲>": {"ope": "⿹", "desc": "右上から囲む構造",       "canonical": []},
    "<IDS左下囲>": {"ope": "⿺", "desc": "左下から囲む構造",       "canonical": []},
    "<IDS重畳>":   {
        "ope": "⿻", "desc": "二字を同位置に重ね合わせる",
        "canonical": [{"tx": 0, "ty": 0, "sx": 1.0}, {"tx": 0, "ty": 0, "sx": 1.0}],
    },
}


def detect_ids_token(record):
    """
    記録から最も近い IDS 演算子トークンを返す。
    単漢字の場合は None（IDS演算子は2字以上の複合構造のため）。
    """
    insts = record.get("instances", [])
    n     = len(insts)
    if n <= 1:
        return None

    chars = [i["char"] for i in insts if "char" in i]
    txs   = [i.get("transform", {}).get("tx", 0) for i in insts]
    tys   = [i.get("transform", {}).get("ty", 0) for i in insts]

    if n == 2:
        dx   = abs(txs[0] - txs[1])
        dy   = abs(tys[0] - tys[1])
        dist = (dx**2 + dy**2) ** 0.5
        if dist < 20:
            return "<IDS重畳>"
        elif dx > dy:
            return "<IDS左右>"
        else:
            return "<IDS上下>"

    if n == 3:
        # 横方向の分散が縦より大きければ左中右、そうでなければ上中下
        tx_range = max(txs) - min(txs)
        ty_range = max(tys) - min(tys)
        return "<IDS左中右>" if tx_range >= ty_range else "<IDS上中下>"

    # n >= 4: 最も近い近似
    return "<IDS左中右>"


def compute_ids_deviation(record, ids_token):
    """
    実際の配置と IDS 標準値の差分を文字列で返す。
    例: ['「超」tx-2, scale-0.15', '「越」tx+2']
    """
    info = IDS_TOKEN_INFO.get(ids_token, {})
    canon = info.get("canonical", [])
    insts = record.get("instances", [])

    if not canon or len(insts) != len(canon):
        return []

    deviations = []
    for i, inst in enumerate(insts):
        t      = inst.get("transform", {})
        a_tx   = t.get("tx", 0)
        a_ty   = t.get("ty", 0)
        a_sx   = t.get("scaleX", t.get("scale", 1.0))
        c      = canon[i]
        dtx    = round(a_tx - c["tx"], 1)
        dty    = round(a_ty - c["ty"], 1)
        dsx    = round(a_sx - c["sx"], 3)
        parts  = []
        if abs(dtx) > 3:  parts.append(f"tx{'+' if dtx > 0 else ''}{dtx}")
        if abs(dty) > 3:  parts.append(f"ty{'+' if dty > 0 else ''}{dty}")
        if abs(dsx) > 0.05: parts.append(f"scale{'+' if dsx > 0 else ''}{dsx:.2f}")
        char = inst.get("char", "?")
        if parts:
            deviations.append(f"「{char}」: {', '.join(parts)}")
        else:
            deviations.append(f"「{char}」: 標準値に近い")
    return deviations


def compute_relative_metrics(record):
    """
    複数インスタンスの相対配置・スケール・重心を計算する。
    省略後の実際の描画領域（bbox）を優先して使用する。
    単漢字の場合は None を返す。
    """
    insts = record.get("instances", [])
    if len(insts) < 2:
        return None

    items = []
    for inst in insts:
        bbox = inst.get("bbox")
        t = inst.get("transform", {})
        if bbox and bbox.get("w", 0) > 1 and bbox.get("h", 0) > 1:
            cx = bbox["x"] + bbox["w"] / 2
            cy = bbox["y"] + bbox["h"] / 2
            area = bbox["w"] * bbox["h"]
        else:
            cx = t.get("tx", 0) + CANVAS_CENTER
            cy = t.get("ty", 0) + CANVAS_CENTER
            area = 900.0  # フォールバック（30×30推定）
        items.append({
            "char":  inst.get("char", "?"),
            "cx":    cx,
            "cy":    cy,
            "area":  area,
            "scale": t.get("scale", 1.0),
        })

    # 全体重心（面積重み付け）
    total_area = sum(it["area"] for it in items)
    gcx = sum(it["cx"] * it["area"] for it in items) / total_area
    gcy = sum(it["cy"] * it["area"] for it in items) / total_area

    def direction(cx, cy):
        h = "左" if cx < 45 else ("右" if cx > 64 else "")
        v = "上" if cy < 45 else ("下" if cy > 64 else "")
        return (h + v) or "中央"

    max_scale = max(it["scale"] for it in items) or 1.0
    placements = []
    for it in items:
        rel_s = round(it["scale"] / max_scale, 2)
        scale_note = f"×{rel_s}" if rel_s < 0.95 else ""
        placements.append(f"「{it['char']}」{direction(it['cx'], it['cy'])}{scale_note}")

    return {
        "placements":  placements,
        "gravity_dir": direction(gcx, gcy),
        "gravity_cx":  round(gcx, 1),
        "gravity_cy":  round(gcy, 1),
    }


def compute_overlap_metrics(record):
    """
    複数インスタンス間の bbox 重なり率・まとまり度を計算する。
    - 各ペアの重なり率: 交差面積 / 小さい方の面積
    - まとまり度: Σ個別面積 / 包絡ボックス面積（1.0 = 完全充填）
    """
    insts = record.get("instances", [])
    if len(insts) < 2:
        return None

    boxes = []
    for inst in insts:
        bbox = inst.get("bbox")
        t = inst.get("transform", {})
        if bbox and bbox.get("w", 0) > 1 and bbox.get("h", 0) > 1:
            x1, y1 = bbox["x"], bbox["y"]
            x2, y2 = bbox["x"] + bbox["w"], bbox["y"] + bbox["h"]
        else:
            cx = t.get("tx", 0) + CANVAS_CENTER
            cy = t.get("ty", 0) + CANVAS_CENTER
            s  = t.get("scale", 1.0)
            half = 25 * s
            x1, y1, x2, y2 = cx - half, cy - half, cx + half, cy + half
        area = max((x2 - x1) * (y2 - y1), 1.0)
        boxes.append({"char": inst.get("char", "?"), "x1": x1, "y1": y1, "x2": x2, "y2": y2, "area": area})

    # ペアごとの重なり率
    overlap_parts = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            ix1, iy1 = max(a["x1"], b["x1"]), max(a["y1"], b["y1"])
            ix2, iy2 = min(a["x2"], b["x2"]), min(a["y2"], b["y2"])
            if ix2 > ix1 and iy2 > iy1:
                inter = (ix2 - ix1) * (iy2 - iy1)
                ratio = round(inter / min(a["area"], b["area"]), 2)
            else:
                ratio = 0.0
            overlap_parts.append({"chars": f"「{a['char']}」「{b['char']}」", "ratio": ratio})

    # まとまり度: Σ個別面積 / 包絡ボックス面積
    all_x1 = min(b["x1"] for b in boxes)
    all_y1 = min(b["y1"] for b in boxes)
    all_x2 = max(b["x2"] for b in boxes)
    all_y2 = max(b["y2"] for b in boxes)
    envelope = max((all_x2 - all_x1) * (all_y2 - all_y1), 1.0)
    cohesion = round(sum(b["area"] for b in boxes) / envelope, 2)

    return {"overlap_parts": overlap_parts, "cohesion": cohesion}


def make_format_e(record, scores):
    """
    特殊トークンを使った ChainOfThought 形式の学習データを生成。

    <思考>
    <解説> テーマ語への批評的読解（interpretation フィールド）
    <概念> 解説から抽出した核心概念
    <選択> 漢字・筆画選択の理由
    <構造> <IDSトークン> 基準値からの逸脱記述
    </思考>
    {JSON}

    interpretation は「解説」として扱う:
      それはテーマ語への偏見・解釈・配慮を込めた批評的読解であり、
      概念・選択・構造はすべてこの解説を基盤として動いている。
    """
    interp = record.get("interpretation", "").strip()
    if not interp or len(interp) < COT_INTERP_MIN_LEN:
        return None

    out = format_record_json(record)
    if not out:
        return None

    theme  = record.get("theme", "")
    insts  = record.get("instances", [])
    chars  = [i["char"] for i in insts if "char" in i]
    chars_str = "・".join(dict.fromkeys(chars))

    # 除去情報
    removal_notes = []
    for inst in insts:
        ab    = inst.get("abstraction", {})
        total = ab.get("totalStrokes", 0)
        rem   = ab.get("removed", 0)
        ri    = [s["index"] for s in inst.get("strokes", []) if s.get("op") == "remove"]
        if total > 0 and rem > 0:
            ratio = rem / total
            removal_notes.append(
                f"「{inst['char']}」{rem}/{total}画除去（{ratio:.0%}）index={ri}"
            )

    # <解説>: interpretation をそのまま使用（批評的読解として）
    kaisetsu_text = interp

    # <概念>: 解説の核心を1行で（先頭の文か全体の要約）
    sentences = [s.strip() for s in interp.replace('。', '。\n').split('\n') if s.strip()]
    concept_text = sentences[0] if sentences else interp[:60]

    # <選択>: 使用漢字 + 解説との対応 + 筆画除去情報
    removal_str = "、".join(removal_notes) if removal_notes else "筆画除去なし"
    selection_text = f"{chars_str}を選択。{removal_str}"

    # <構造>: IDS基準トークン + 逸脱記述 + 相対配置・重心 + 重なり・まとまり
    ids_token = detect_ids_token(record)
    rel       = compute_relative_metrics(record)
    ov        = compute_overlap_metrics(record)

    if ids_token:
        ids_info   = IDS_TOKEN_INFO[ids_token]
        deviations = compute_ids_deviation(record, ids_token)
        dev_str    = "、".join(deviations) if deviations else "標準配置"
        structure_text = (
            f"{ids_token}（{ids_info['ope']} {ids_info['desc']}）基準。"
            f"逸脱: {dev_str}"
        )
    else:
        total_st = sum(i.get("abstraction", {}).get("totalStrokes", 0) for i in insts)
        removed  = sum(i.get("abstraction", {}).get("removed", 0) for i in insts)
        ratio    = removed / total_st if total_st > 0 else 0.0
        structure_text = (
            f"単漢字構造（IDS演算子なし）。"
            f"除去率{ratio:.0%}{'（骨格抽出）' if ratio >= 0.5 else '（部分除去）'}"
        )

    # 相対配置・重心を追記（2字以上の場合）
    if rel:
        place_str = "、".join(rel["placements"])
        structure_text += (
            f"。配置: {place_str}。"
            f"重心: {rel['gravity_dir']}({rel['gravity_cx']},{rel['gravity_cy']})"
        )

    # 重なり率・まとまり度を追記（2字以上の場合）
    if ov:
        ov_strs = []
        for part in ov["overlap_parts"]:
            r = part["ratio"]
            if r >= 0.5:
                ov_strs.append(f"{part['chars']}重畳{int(r*100)}%")
            elif r >= 0.1:
                ov_strs.append(f"{part['chars']}部分重なり{int(r*100)}%")
            else:
                ov_strs.append(f"{part['chars']}非重複")
        c = ov["cohesion"]
        cohesion_label = "高まとまり" if c >= 0.7 else ("中まとまり" if c >= 0.4 else "分散")
        structure_text += (
            f"。重なり: {'、'.join(ov_strs)}。"
            f"まとまり度: {cohesion_label}({c})"
        )

    cot_block = (
        f"<思考>\n"
        f"<解説> {kaisetsu_text}\n"
        f"<概念> {concept_text}\n"
        f"<選択> {selection_text}\n"
        f"<構造> {structure_text}\n"
        f"</思考>\n"
        f"{json.dumps(out, ensure_ascii=False)}"
    )

    return {
        "messages": [
            {"role": "system",    "content": SYSTEM_PROMPT},
            {"role": "user",      "content": FORMAT_A_USER.format(theme=theme)},
            {"role": "assistant", "content": cot_block},
        ]
    }


# ─── メイン ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("  IDS Fine-tune Data Preparation  v2")
    print("=" * 50)

    records = load_all_quality_records()
    print(f"\n品質フィルタ後: {len(records)} records")
    src_counts = Counter(r["_source"] for r in records)
    for s, c in src_counts.items():
        print(f"  {s}: {c}")

    research = load_research()
    if research:
        print(f"研究データ: {len(research.get('patterns', []))} patterns")
    else:
        print("研究データなし（auto_research.py を先に実行してください）")

    scores = load_scores()

    examples = []
    skipped  = 0

    # Format A（品質重み付け込み）
    count_a = 0
    count_a_dup = 0
    for r in records:
        ex = make_format_a(r)
        if ex:
            examples.append(("A", ex))
            count_a += 1
            # 高品質記録は 3x 重複
            k = record_key(r)
            sc = scores.get(k, {})
            total_score = sc.get("graphic", 0) + sc.get("abstraction", 0)
            if total_score >= HIGH_QUALITY_MIN:
                for _ in range(2):  # 追加 2 件 → 計 3 件
                    examples.append(("A+", ex))
                    count_a_dup += 1
        else:
            skipped += 1
    print(f"\nFormat A (お題→生成):        {count_a} 件  (高品質重複 +{count_a_dup} 件)")

    # Format B
    count_b = 0
    for r in records:
        ex = make_format_b(r)
        if ex:
            examples.append(("B", ex))
            count_b += 1
    print(f"Format B (記号→解説):        {count_b} 件")

    # Format C
    count_c = 0
    if research:
        records_by_tag = {}
        for r in records:
            insts = r.get("instances", [])
            n     = len(insts)
            chars = [i["char"] for i in insts if "char" in i]
            if n == 1:
                tag = "single_intact"
            elif n == 2:
                tag = "repeated_overlap" if len(set(chars)) == 1 else "dual_overlap"
            elif n == 3:
                tag = "triple_composition"
            else:
                tag = "multi_kanji"
            records_by_tag.setdefault(tag, []).append(r)

        for pattern in research.get("patterns", []):
            for ex in make_format_c(pattern, records_by_tag):
                examples.append(("C", ex))
                count_c += 1
    print(f"Format C (構造パターン問答): {count_c} 件")

    # Format D
    d_examples = make_format_d()
    for ex in d_examples:
        examples.append(("D", ex))
    print(f"Format D (創作哲学問答):     {len(d_examples)} 件")

    # Format E: ChainOfThought
    count_e = 0
    for r in records:
        ex = make_format_e(r, scores)
        if ex:
            examples.append(("E", ex))
            count_e += 1
    print(f"Format E (CoT 思考過程):     {count_e} 件")

    total = len(examples)
    print(f"\n合計: {total} 件（スキップ: {skipped}）")

    # シャッフル & 90/10 分割
    random.seed(42)
    random.shuffle(examples)
    split = max(1, int(total * 0.9))
    train = [ex for _, ex in examples[:split]]
    valid = [ex for _, ex in examples[split:]]
    if not valid:
        valid = [train.pop()]

    train_path = DATA_DIR / "train.jsonl"
    valid_path = DATA_DIR / "valid.jsonl"

    with open(train_path, "w", encoding="utf-8") as f:
        for ex in train:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    with open(valid_path, "w", encoding="utf-8") as f:
        for ex in valid:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"\n出力:")
    print(f"  {train_path}  ({len(train)} 件)")
    print(f"  {valid_path} ({len(valid)} 件)")

    fmt_counts = Counter(fmt for fmt, _ in examples)
    print(f"内訳: " + "  ".join(f"{k}={v}" for k, v in sorted(fmt_counts.items())))

    # サンプル表示
    for label, fmt_code in [("Format A", "A"), ("Format B", "B"), ("Format C", "C"), ("Format D", "D"), ("Format E (CoT)", "E")]:
        for fmt, ex in examples:
            if fmt == fmt_code:
                u = ex["messages"][1]["content"][:70]
                a = ex["messages"][2]["content"][:80]
                print(f"\n--- {label} サンプル ---")
                print(f"  USER: {u}...")
                print(f"  ASST: {a}...")
                break

    print("\n完了。run_finetune.sh を実行してファインチューニングを開始してください。")


if __name__ == "__main__":
    main()
