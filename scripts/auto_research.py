#!/usr/bin/env python3
"""
auto_research.py — IDS Symbol Renderer structural pattern discovery
Two-stage analysis:
  Stage 1 (rule-based):  classify by known IDS/spatial structure types
  Stage 2 (unsupervised): k-means on rich feature vectors → discover novel groups
Output: research/patterns.json
"""

import json
import math
import sys
import urllib.request
from collections import defaultdict, Counter
from pathlib import Path

import numpy as np

# ── paths ────────────────────────────────────────────────────────────────────
BASE         = Path(__file__).resolve().parent.parent
RESULTS_FILES = {
    "human":  BASE / "results.jsonl",
    "ai":     BASE / "ai_results.jsonl",
    "hybrid": BASE / "hybrid_results.jsonl",
}
SCORES_FILE  = BASE / "scores.json"
TRASH_FILE   = BASE / "trash.jsonl"
OUTPUT_FILE  = BASE / "research" / "patterns.json"

MLX_BASE_URL      = "http://localhost:11435/v1"
MODEL_NAME        = "mlx-community/Qwen3-4B-IDS-fused-4bit"
QUALITY_THRESHOLD = 10   # G+A score required for AI/hybrid records


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_jsonl(path):
    records = []
    if not path.exists():
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def load_all_records():
    scores = {}
    if SCORES_FILE.exists():
        with open(SCORES_FILE, encoding="utf-8") as f:
            scores = json.load(f)

    trash_set = set()
    for r in load_jsonl(TRASH_FILE):
        k = r.get("symbol_id") or r.get("timestamp")
        if k:
            trash_set.add(k)

    records = []
    for source, path in RESULTS_FILES.items():
        for r in load_jsonl(path):
            k = r.get("symbol_id") or r.get("timestamp")
            if k and k in trash_set:
                continue
            r["_source"] = source
            if source == "human":
                records.append(r)
            else:
                s = scores.get(k, {})
                if s.get("graphic", 0) + s.get("abstraction", 0) >= QUALITY_THRESHOLD:
                    records.append(r)
    return records


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE EXTRACTION  (rule-based + numerical vector)
# ═══════════════════════════════════════════════════════════════════════════════

def removal_ratio(ab):
    total = ab.get("totalStrokes", 0)
    return ab.get("removed", 0) / total if total else 0.0


def stroke_position_bias(inst):
    """Returns (early_ratio, late_ratio) of removed strokes by index position."""
    ab   = inst.get("abstraction", {})
    total = ab.get("totalStrokes", 0)
    if total == 0:
        return 0.0, 0.0
    removed = ab.get("removedIndices", [])
    if not removed:
        return 0.0, 0.0
    mid = total / 2.0
    early = sum(1 for i in removed if i < mid)
    late  = len(removed) - early
    n = len(removed)
    return early / n, late / n


def containment_score(inst_a, inst_b):
    """
    Returns 0-1: how much is inst_b "inside" the visual bounding area of inst_a.
    Uses a simple Gaussian proximity model.
    Positive score = b is nested inside a.
    """
    tr_a = inst_a.get("transform", {})
    tr_b = inst_b.get("transform", {})
    sx_a = abs(tr_a.get("scaleX", 1)) * 50
    sy_a = abs(tr_a.get("scaleY", 1)) * 50
    dx   = tr_b.get("tx", 0) - tr_a.get("tx", 0)
    dy   = tr_b.get("ty", 0) - tr_a.get("ty", 0)
    # normalised distance inside a's bounding box
    nx = dx / sx_a if sx_a > 0 else 99
    ny = dy / sy_a if sy_a > 0 else 99
    dist_norm = math.sqrt(nx * nx + ny * ny)
    # score: 1.0 if perfectly centred inside, falls off with distance
    return max(0.0, 1.0 - dist_norm)


def extract_features(record):
    instances = record.get("instances", [])
    n = len(instances)
    if n == 0:
        return None

    chars      = [inst.get("char", "?") for inst in instances]
    char_counts = Counter(chars)

    inst_feats = []
    for inst in instances:
        tr = inst.get("transform", {})
        ab = inst.get("abstraction", {})
        rr = removal_ratio(ab)
        eb, lb = stroke_position_bias(inst)
        inst_feats.append({
            "char":         inst.get("char", "?"),
            "tx":           tr.get("tx", 0),
            "ty":           tr.get("ty", 0),
            "rotate":       tr.get("rotate", 0),
            "scaleX":       tr.get("scaleX", 1),
            "scaleY":       tr.get("scaleY", 1),
            "removal_ratio": rr,
            "early_bias":   eb,    # removed strokes are front-loaded
            "late_bias":    lb,    # removed strokes are back-loaded
            "total_strokes": ab.get("totalStrokes", 0),
        })

    # ---------- pairwise geometry ----------
    positions  = [(f["tx"], f["ty"])           for f in inst_feats]
    areas      = [abs(f["scaleX"] * f["scaleY"]) for f in inst_feats]

    pair_dists = []
    containment_scores = []
    scale_contrasts    = []

    if n >= 2:
        for i in range(n):
            for j in range(i + 1, n):
                dx = positions[i][0] - positions[j][0]
                dy = positions[i][1] - positions[j][1]
                pair_dists.append(math.sqrt(dx*dx + dy*dy))
                # containment: smaller inside larger
                if areas[i] >= areas[j]:
                    containment_scores.append(
                        containment_score(instances[i], instances[j]))
                else:
                    containment_scores.append(
                        containment_score(instances[j], instances[i]))
                sc = max(areas[i], areas[j]) / (min(areas[i], areas[j]) + 0.001)
                scale_contrasts.append(sc)

    max_dist    = max(pair_dists)          if pair_dists else 0.0
    min_dist    = min(pair_dists)          if pair_dists else 0.0
    max_contain = max(containment_scores)  if containment_scores else 0.0
    max_sc_cont = max(scale_contrasts)     if scale_contrasts else 1.0

    avg_removal = sum(f["removal_ratio"] for f in inst_feats) / n
    max_removal = max(f["removal_ratio"] for f in inst_feats)
    removal_var = (
        sum((f["removal_ratio"] - avg_removal) ** 2 for f in inst_feats) / n
        if n > 1 else 0.0
    )
    has_rotation    = any(abs(f["rotate"]) > 1   for f in inst_feats)
    has_anisotropic = any(abs(f["scaleX"] - f["scaleY"]) > 0.25 for f in inst_feats)
    has_repeated    = any(v > 1 for v in char_counts.values())

    max_dx = max_dy = 0.0
    if n >= 2:
        for i in range(n):
            for j in range(i+1, n):
                max_dx = max(max_dx, abs(positions[i][0] - positions[j][0]))
                max_dy = max(max_dy, abs(positions[i][1] - positions[j][1]))

    is_complementary = (
        n == 2
        and inst_feats[0]["removal_ratio"] > 0.3
        and inst_feats[1]["removal_ratio"] > 0.3
    )

    return {
        # used for rule classification
        "kanji_count":        n,
        "chars":              chars,
        "char_counts":        dict(char_counts),
        "has_repeated_kanji": has_repeated,
        "has_rotation":       has_rotation,
        "has_anisotropic":    has_anisotropic,
        "avg_removal_ratio":  avg_removal,
        "max_removal_ratio":  max_removal,
        "is_complementary":   is_complementary,
        "max_dx":             max_dx,
        "max_dy":             max_dy,
        "max_dist":           max_dist,
        "instances":          inst_feats,
        # used for vector clustering
        "removal_var":        removal_var,
        "max_containment":    max_contain,
        "max_scale_contrast": max_sc_cont,
        "min_dist":           min_dist,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RULE-BASED CLASSIFICATION  (stage 1)
# ═══════════════════════════════════════════════════════════════════════════════

def classify_structure(feat):
    n   = feat["kanji_count"]
    mxr = feat["max_removal_ratio"]
    dx  = feat["max_dx"]
    dy  = feat["max_dy"]
    md  = feat["max_dist"]
    tags = []

    if n == 1:
        tags.append(
            "single_heavy_removal" if mxr >= 0.6 else
            "single_partial_removal" if mxr >= 0.3 else
            "single_intact"
        )
    elif n == 2:
        if feat["has_repeated_kanji"]:
            tags.append("repeated_overlap" if md < 25 else
                        "repeated_horizontal" if dx > dy else "repeated_vertical")
        else:
            if md < 25:
                tags.append("dual_overlap")
            elif feat["is_complementary"]:
                tags.append("dual_complementary_horizontal" if dx > dy
                            else "dual_complementary_vertical")
            else:
                if dx > dy + 5:
                    tags.append("dual_horizontal")
                elif dy > dx + 5:
                    tags.append("dual_vertical")
                else:
                    tags.append("dual_diagonal")
    elif n == 3:
        tags.append("triple_repeated" if feat["has_repeated_kanji"]
                    else "triple_composition")
    else:
        tags.append("multi_kanji")

    if feat["has_rotation"]:       tags.append("rotated")
    if feat["has_anisotropic"]:    tags.append("anisotropic_scale")
    return tags


# ═══════════════════════════════════════════════════════════════════════════════
# NUMERICAL FEATURE VECTOR  (stage 2 – unsupervised discovery)
# ═══════════════════════════════════════════════════════════════════════════════

MAX_INST = 4   # pad/truncate to this many instances

def build_vector(feat):
    """
    Returns a fixed-length numpy vector capturing structural geometry.
    All values normalised to roughly [0,1].
    """
    n     = feat["kanji_count"]
    insts = feat["instances"]

    v = []

    # --- global ---
    v.append(min(n, MAX_INST + 1) / (MAX_INST + 1))   # kanji count
    v.append(1.0 if feat["has_repeated_kanji"] else 0.0)
    v.append(1.0 if feat["has_rotation"]       else 0.0)
    v.append(1.0 if feat["has_anisotropic"]    else 0.0)
    v.append(feat["avg_removal_ratio"])
    v.append(feat["max_removal_ratio"])
    v.append(min(feat["removal_var"] * 10, 1.0))  # variance
    v.append(min(feat["max_dist"]  / 100.0, 1.0))
    v.append(min(feat["min_dist"]  / 100.0, 1.0))
    v.append(min(feat["max_containment"], 1.0))
    v.append(min((feat["max_scale_contrast"] - 1.0) / 9.0, 1.0))
    v.append(min(feat["max_dx"] / 60.0, 1.0))
    v.append(min(feat["max_dy"] / 60.0, 1.0))

    # --- per-instance (up to MAX_INST, padded with zeros) ---
    for i in range(MAX_INST):
        if i < len(insts):
            f = insts[i]
            v.append(max(-1, min(1, f["tx"] / 50.0)))
            v.append(max(-1, min(1, f["ty"] / 50.0)))
            v.append(min(abs(f["scaleX"]), 2.0) / 2.0)
            v.append(min(abs(f["scaleY"]), 2.0) / 2.0)
            v.append(f["removal_ratio"])
            v.append(f["early_bias"])
            v.append(f["late_bias"])
            v.append(min(abs(f["rotate"]) / 180.0, 1.0))
        else:
            v.extend([0.0] * 8)

    return np.array(v, dtype=np.float32)


# ═══════════════════════════════════════════════════════════════════════════════
# K-MEANS  (numpy only)
# ═══════════════════════════════════════════════════════════════════════════════

def kmeans(X, k, n_init=10, max_iter=300, tol=1e-4):
    """Returns (labels, centroids, inertia)."""
    best = None
    rng  = np.random.default_rng(42)
    for _ in range(n_init):
        # k-means++ init
        idx = [rng.integers(len(X))]
        for _ in range(k - 1):
            d2 = np.array([min(np.sum((X - X[c]) ** 2) for c in idx)
                           for _ in range(1)])   # slow but simple
            # fast version:
            D = np.min(np.stack(
                [np.sum((X - X[c]) ** 2, axis=1) for c in idx], axis=1
            ), axis=1)
            probs = D / D.sum()
            idx.append(rng.choice(len(X), p=probs))
        centroids = X[np.array(idx)]

        labels = np.zeros(len(X), dtype=int)
        for _ in range(max_iter):
            # assign
            dists   = np.stack(
                [np.sum((X - c) ** 2, axis=1) for c in centroids], axis=1
            )
            new_labels = np.argmin(dists, axis=1)
            if np.all(new_labels == labels):
                break
            labels = new_labels
            # update
            new_centroids = np.array(
                [X[labels == ki].mean(axis=0) if np.any(labels == ki) else centroids[ki]
                 for ki in range(k)]
            )
            shift = np.max(np.sum((new_centroids - centroids) ** 2, axis=1))
            centroids = new_centroids
            if shift < tol:
                break

        inertia = sum(
            np.sum((X[labels == ki] - centroids[ki]) ** 2)
            for ki in range(k) if np.any(labels == ki)
        )
        if best is None or inertia < best[2]:
            best = (labels.copy(), centroids.copy(), inertia)

    return best


def best_k(X, k_range=(4, 16)):
    """Choose k using elbow (second derivative of inertia)."""
    inertias = []
    ks = list(range(k_range[0], k_range[1] + 1))
    for k in ks:
        _, _, inertia = kmeans(X, k, n_init=3)
        inertias.append(inertia)
        print(f"  k={k} inertia={inertia:.1f}", file=sys.stderr)

    # second derivative
    d2 = [inertias[i-1] - 2*inertias[i] + inertias[i+1]
          for i in range(1, len(inertias) - 1)]
    best_idx = int(np.argmax(d2)) + 1
    return ks[best_idx]


# ═══════════════════════════════════════════════════════════════════════════════
# NOVELTY SCORING  – how different is a cluster from rule-based taxonomy
# ═══════════════════════════════════════════════════════════════════════════════

KNOWN_PATTERNS = {
    "single_heavy_removal", "single_partial_removal", "single_intact",
    "dual_overlap", "dual_horizontal", "dual_vertical", "dual_diagonal",
    "dual_complementary_horizontal", "dual_complementary_vertical",
    "repeated_overlap", "repeated_horizontal", "repeated_vertical",
    "triple_composition", "triple_repeated", "multi_kanji",
}

def novelty_score(items):
    """
    0.0 = cluster is dominated by a single known pattern (not novel)
    1.0 = cluster spans many known patterns or has no dominant one (novel)
    """
    rule_tags = [item["tags"][0] for item in items]
    counts = Counter(rule_tags)
    dominant_fraction = counts.most_common(1)[0][1] / len(items)
    # low dominant fraction → cluster cuts across rule categories → novel
    return round(1.0 - dominant_fraction, 3)


# ═══════════════════════════════════════════════════════════════════════════════
# LLM HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def llm_chat(prompt, max_tokens=512):
    payload = json.dumps({
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{MLX_BASE_URL}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as res:
        data = json.loads(res.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def is_llm_available():
    try:
        with urllib.request.urlopen(
            urllib.request.Request(f"{MLX_BASE_URL}/models", method="GET"),
            timeout=3
        ) as res:
            return res.status == 200
    except Exception:
        return False


def extract_json(text):
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except Exception:
            pass
    return None


def analyze_rule_group(tag, examples, use_llm):
    prompt = f"""あなたは漢字記号・文字芸術の研究者です。
以下は「{tag}」という構造パターンに分類された記号作品の例です。

{chr(10).join(f'- {e}' for e in examples[:8])}

このパターンの特徴を分析してください：
1. パターン名（日本語で短く、20字以内）
2. 構造の説明（どのように漢字を変形・組み合わせているか、3文以内）
3. 表現上の効果（なぜこの構造が意味を伝えるのに有効か、2文以内）
4. 発展可能性（このパターンを応用するアイデア、1〜2文）

JSON形式で回答してください:
{{"name": "...", "description": "...", "effect": "...", "potential": "..."}}"""

    if use_llm:
        try:
            r = extract_json(llm_chat(prompt))
            if r:
                return r
        except Exception as e:
            print(f"  [LLM error {tag}]: {e}", file=sys.stderr)

    return {"name": tag, "description": f"{tag}パターン", "effect": "", "potential": ""}


def analyze_discovery_cluster(cluster_id, items, feat_summary, use_llm):
    """
    Ask LLM to discover and name a structural algorithm from a cluster
    that may not fit standard IDS categories.
    """
    examples = []
    for it in items[:10]:
        r = it["record"]
        f = it["feat"]
        theme = r.get("theme", "（なし）")
        interp = r.get("interpretation", "")
        chars = "・".join(f["chars"])
        tx_list = [f"{fi['tx']:.0f},{fi['ty']:.0f}" for fi in f["instances"]]
        rr_list = [f"{fi['removal_ratio']:.0%}" for fi in f["instances"]]
        line = (f"お題「{theme}」 漢字:{chars} "
                f"位置:{'/'.join(tx_list)} 除去率:{'/'.join(rr_list)}")
        if interp:
            line += f" 意図:「{interp[:40]}」"
        examples.append(line)

    rule_distribution = Counter(it["tags"][0] for it in items)

    prompt = f"""あなたは漢字記号・文字芸術の研究者で、未知の構造パターンを発見することが得意です。
以下の記号作品群は、機械学習のクラスタリングによって同じグループに分類されましたが、
既存のIDS（漢字構造記述）分類には当てはまらない可能性があります。

作品例（{len(items)}件中最大10件）:
{chr(10).join(f'  {i+1}. {e}' for i, e in enumerate(examples))}

既存分類との分布: {dict(rule_distribution)}
特徴サマリー:
  - 平均漢字数: {feat_summary['avg_n']:.1f}
  - 平均除去率: {feat_summary['avg_removal']:.0%}
  - 除去率の分散: {feat_summary['removal_var']:.3f}（高いほど各漢字で異なる除去戦略）
  - 最大重なり具合: {feat_summary['max_containment']:.2f}（高いほど入れ子構造に近い）
  - スケール対比: {feat_summary['scale_contrast']:.2f}（高いほど漢字間サイズ差が大きい）
  - 回転あり: {'はい' if feat_summary['has_rotation'] else 'いいえ'}

【重要】これらの作品に共通する「構造アルゴリズム」を発見・命名してください。
既存IDS構造（左右組合せ、上下組合せ、囲み構造など）に縛られず、
この作者が独自に開発したかもしれない新しい構造原理を探してください。

JSON形式で回答してください（novelty_scoreは0-1で新規性の高さ）:
{{
  "name": "発見した構造の名前（日本語20字以内）",
  "algorithm": "この構造がどう機能するかのアルゴリズム的説明（3-5文）",
  "visual_principle": "視覚的にどう見えるか、どんな効果があるか（2-3文）",
  "ids_relation": "既存IDS構造との関係・違い（1-2文）",
  "novel_aspect": "この構造の最も独自な点（1文）",
  "novelty_score": 0.0
}}"""

    if use_llm:
        try:
            r = extract_json(llm_chat(prompt, max_tokens=600))
            if r:
                return r
        except Exception as e:
            print(f"  [LLM error cluster {cluster_id}]: {e}", file=sys.stderr)

    return {
        "name":           f"クラスタ{cluster_id}",
        "algorithm":      "（LLM未使用のため分析なし）",
        "visual_principle": "",
        "ids_relation":   "",
        "novel_aspect":   "",
        "novelty_score":  feat_summary.get("novelty_score", 0.0),
    }


def analyze_philosophy(records, use_llm):
    texts = [r.get("interpretation", "").strip()
             for r in records if r.get("interpretation", "").strip()]
    if not texts:
        return {"summary": "制作意図の記録なし"}
    sample = texts[:20]
    prompt = f"""漢字記号作品{len(texts)}件の制作意図から、作者の創作哲学を200字以内で総括してください。
{chr(10).join(f'「{t}」' for t in sample)}"""
    if use_llm:
        try:
            return {"summary": llm_chat(prompt, max_tokens=300)}
        except Exception as e:
            print(f"  [LLM philosophy error]: {e}", file=sys.stderr)
    return {"summary": f"{len(texts)}件の制作意図を分析（LLM未使用）"}


# ═══════════════════════════════════════════════════════════════════════════════
# EXAMPLE TEXT BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def build_example_text(record, feat):
    theme  = record.get("theme", "（なし）")
    interp = record.get("interpretation", "")
    chars  = "・".join(feat["chars"])
    rr_pct = int(feat["avg_removal_ratio"] * 100)
    parts  = [f"お題「{theme}」 使用漢字: {chars} (平均除去率{rr_pct}%)"]
    if interp:
        parts.append(f"制作意図: {interp[:50]}")
    return " / ".join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def run():
    print("=== IDS Symbol Auto-Research ===")

    records = load_all_records()
    print(f"Records: {len(records)}")
    if not records:
        print("No records."); sys.exit(1)

    use_llm = is_llm_available()
    print(f"LLM: {'available' if use_llm else 'offline'}")

    # ── Feature extraction ────────────────────────────────────────────────────
    annotated = []
    for r in records:
        feat = extract_features(r)
        if feat is None:
            continue
        tags = classify_structure(feat)
        vec  = build_vector(feat)
        annotated.append({"record": r, "feat": feat, "tags": tags, "vec": vec})

    print(f"Feature extraction: {len(annotated)} records")

    # ────────────────────────────────────────────────────────────────────────
    # STAGE 1: rule-based groups
    # ────────────────────────────────────────────────────────────────────────
    print("\n── Stage 1: rule-based classification ──")
    rule_groups = defaultdict(list)
    for item in annotated:
        rule_groups[item["tags"][0]].append(item)

    def record_key(r):
        return r.get("symbol_id") or r.get("timestamp") or ""

    patterns = []
    for tag, items in sorted(rule_groups.items(), key=lambda x: -len(x[1])):
        print(f"  [{tag}] {len(items)}")
        examples   = [build_example_text(it["record"], it["feat"]) for it in items]
        char_freq  = Counter(c for it in items for c in it["feat"]["chars"])
        avg_removal = sum(it["feat"]["avg_removal_ratio"] for it in items) / len(items)
        llm_r       = analyze_rule_group(tag, examples, use_llm)
        patterns.append({
            "tag":              tag,
            "count":            len(items),
            "name":             llm_r.get("name", tag),
            "description":      llm_r.get("description", ""),
            "effect":           llm_r.get("effect", ""),
            "potential":        llm_r.get("potential", ""),
            "avg_removal_ratio": round(avg_removal, 3),
            "top_chars":        char_freq.most_common(10),
            "examples_sample":  examples[:5],
            "modifier_tags":    list({t for it in items for t in it["tags"][1:]}),
            "record_ids":       [record_key(it["record"]) for it in items],
        })

    # ────────────────────────────────────────────────────────────────────────
    # STAGE 2: unsupervised discovery
    # ────────────────────────────────────────────────────────────────────────
    print("\n── Stage 2: unsupervised discovery ──")
    X = np.stack([item["vec"] for item in annotated])

    # Normalise features column-wise
    col_std = X.std(axis=0)
    col_std[col_std < 1e-6] = 1.0
    X_norm = (X - X.mean(axis=0)) / col_std

    print(f"  Finding best k in range 5-14…", file=sys.stderr)
    k = best_k(X_norm, k_range=(5, 14))
    print(f"  Selected k={k}")

    labels, centroids, _ = kmeans(X_norm, k, n_init=8)

    # Build clusters
    clusters = defaultdict(list)
    for i, lbl in enumerate(labels):
        clusters[int(lbl)].append(annotated[i])

    discoveries = []
    for cid, items in sorted(clusters.items(), key=lambda x: -len(x[1])):
        nov = novelty_score(items)
        avg_n        = sum(it["feat"]["kanji_count"]      for it in items) / len(items)
        avg_removal  = sum(it["feat"]["avg_removal_ratio"] for it in items) / len(items)
        removal_var  = sum(it["feat"]["removal_var"]       for it in items) / len(items)
        max_contain  = sum(it["feat"]["max_containment"]   for it in items) / len(items)
        sc_avg       = sum(it["feat"]["max_scale_contrast"] for it in items) / len(items)
        has_rotation = sum(1 for it in items if it["feat"]["has_rotation"]) / len(items)
        rule_dist    = Counter(it["tags"][0] for it in items)

        feat_summary = {
            "avg_n":           round(avg_n, 2),
            "avg_removal":     round(avg_removal, 3),
            "removal_var":     round(removal_var, 4),
            "max_containment": round(max_contain, 3),
            "scale_contrast":  round(sc_avg, 2),
            "has_rotation":    has_rotation > 0.3,
            "novelty_score":   nov,
        }

        print(f"  [cluster {cid}] {len(items)} items, novelty={nov:.2f}, "
              f"rule_dist={dict(rule_dist)}")

        llm_r = analyze_discovery_cluster(cid, items, feat_summary, use_llm)

        discoveries.append({
            "cluster_id":       cid,
            "count":            len(items),
            "novelty_score":    nov,
            "name":             llm_r.get("name", f"クラスタ{cid}"),
            "algorithm":        llm_r.get("algorithm", ""),
            "visual_principle": llm_r.get("visual_principle", ""),
            "ids_relation":     llm_r.get("ids_relation", ""),
            "novel_aspect":     llm_r.get("novel_aspect", ""),
            "llm_novelty":      llm_r.get("novelty_score", nov),
            "rule_distribution": dict(rule_dist),
            "feat_summary":     feat_summary,
            "examples_sample":  [build_example_text(it["record"], it["feat"])
                                  for it in items[:5]],
            "record_ids":       [record_key(it["record"]) for it in items],
        })

    # sort by novelty descending
    discoveries.sort(key=lambda d: -d["novelty_score"])

    # ────────────────────────────────────────────────────────────────────────
    # Philosophy
    # ────────────────────────────────────────────────────────────────────────
    print("\nAnalyzing creative philosophy…")
    philosophy = analyze_philosophy(records, use_llm)

    # ────────────────────────────────────────────────────────────────────────
    # Overall stats
    # ────────────────────────────────────────────────────────────────────────
    total_chars = Counter(c for it in annotated for c in it["feat"]["chars"])

    output = {
        "generated_at":    __import__("datetime").datetime.now().isoformat(),
        "total_records":   len(annotated),
        "llm_used":        use_llm,
        "philosophy":      philosophy,
        "patterns":        patterns,          # stage 1: rule-based
        "discoveries":     discoveries,       # stage 2: novel clusters
        "top_chars_overall": total_chars.most_common(20),
        "kanji_count_distribution": dict(
            Counter(it["feat"]["kanji_count"] for it in annotated)
        ),
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ {OUTPUT_FILE}")
    print(f"  Stage 1: {len(patterns)} rule-based patterns")
    print(f"  Stage 2: {len(discoveries)} discovered clusters "
          f"(top novelty: {discoveries[0]['novelty_score']:.2f} "
          f"'{discoveries[0]['name']}')")
    return output


if __name__ == "__main__":
    run()
