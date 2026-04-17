#!/usr/bin/env python3
"""
extend_tokenizer.py
Qwen3-4B のトークナイザーに思考ステップトークンと IDS 構造トークンを追加し、
base モデルの埋め込み層を拡張して保存する。

追加トークン (18個):
  思考ステップ: <思考> </思考> <解説> <概念> <選択> <構造>
  IDS 12演算子: <IDS左右> <IDS上下> <IDS左中右> <IDS上中下>
               <IDS全囲> <IDS上囲> <IDS下囲> <IDS左囲>
               <IDS左上囲> <IDS右上囲> <IDS左下囲> <IDS重畳>

設計思想:
  IDS12トークンは分類ラベルではなく「参照基準」。
  <構造>ブロック内でどのIDS演算子を基準とし、
  実際の配置がそこからどれだけ逸脱しているかを記述する。
  <解説>はテーマ語への批評的読解層（偏見・解釈・配慮）を格納する。
"""

import json
import shutil
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
BASE_DIR  = ROOT / "models" / "Qwen3-32B"
OUT_DIR   = ROOT / "models" / "Qwen3-32B-extended"

NEW_TOKENS = [
    # ── 思考ステップ ──────────────────────────────────────────────────────
    "<思考>", "</思考>",
    "<解説>",    # テーマ語への批評的読解（偏見・解釈・配慮）
    "<概念>",    # 解説から抽出した核心概念
    "<選択>",    # 漢字・筆画選択の理由（意味層・筆画層・関係層）
    "<構造>",    # IDS基準トークン + 標準値からの逸脱記述
    # ── IDS 12演算子（参照基準として） ───────────────────────────────────
    "<IDS左右>",    # ⿰  Left to Right
    "<IDS上下>",    # ⿱  Above to Below
    "<IDS左中右>",  # ⿲  Left to Middle and Right
    "<IDS上中下>",  # ⿳  Above to Middle and Below
    "<IDS全囲>",    # ⿴  Full Surround
    "<IDS上囲>",    # ⿵  Surround from Above
    "<IDS下囲>",    # ⿶  Surround from Below
    "<IDS左囲>",    # ⿷  Surround from Left
    "<IDS左上囲>",  # ⿸  Surround from Upper Left
    "<IDS右上囲>",  # ⿹  Surround from Upper Right
    "<IDS左下囲>",  # ⿺  Surround from Lower Left
    "<IDS重畳>",    # ⿻  Overlaid
]


def extend_tokenizer_json(src: Path, dst: Path, new_tokens: list[str]):
    """
    tokenizers ライブラリの正規API でトークンを追加して保存。
    JSON 手動操作を避けることで Rust パーサの互換性を保つ。
    """
    from tokenizers import Tokenizer, AddedToken

    tok = Tokenizer.from_file(str(src))

    existing = {tok.id_to_token(i) for i in range(tok.get_vocab_size())}
    to_add = [t for t in new_tokens if t not in existing]
    skipped = [t for t in new_tokens if t in existing]
    for t in skipped:
        print(f"  skip (already exists): {t}")

    if to_add:
        added_tokens = [
            AddedToken(t, special=True, normalized=False, single_word=False,
                       lstrip=False, rstrip=False)
            for t in to_add
        ]
        tok.add_special_tokens(added_tokens)

    for t in to_add:
        tid = tok.token_to_id(t)
        print(f"  + {t!r} → id {tid}")

    new_vocab_size = tok.get_vocab_size()
    dst.mkdir(parents=True, exist_ok=True)
    tok.save(str(dst / "tokenizer.json"))

    print(f"  {len(to_add)} tokens added. New vocab size: {new_vocab_size}")
    return len(to_add), new_vocab_size


def extend_config(src: Path, dst: Path, new_vocab_size: int):
    """config.json の vocab_size を更新（縮小はしない）。"""
    with open(src / "config.json", encoding="utf-8") as f:
        cfg = json.load(f)
    old_size   = cfg.get("vocab_size", 0)
    final_size = max(new_vocab_size, old_size)
    cfg["vocab_size"] = final_size
    with open(dst / "config.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print(f"  config.json: vocab_size → {final_size}"
          + (f"  (kept original {old_size}, new tokens fit within existing space)"
             if final_size == old_size else ""))


def extend_tokenizer_config(src: Path, dst: Path, new_tokens: list[str]):
    """tokenizer_config.json の additional_special_tokens に新トークンを追加。
    Qwen2Tokenizer（スロートークナイザー）が special tokens を認識するために必要。"""
    with open(src / "tokenizer_config.json", encoding="utf-8") as f:
        cfg = json.load(f)
    existing = set(cfg.get("additional_special_tokens", []))
    to_add   = [t for t in new_tokens if t not in existing]
    cfg.setdefault("additional_special_tokens", []).extend(to_add)
    with open(dst / "tokenizer_config.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print(f"  tokenizer_config.json: added {len(to_add)} tokens to additional_special_tokens")


def copy_other_files(src: Path, dst: Path):
    """モデルファイル以外をコピー（重いsafetensors・ディレクトリは除く）。"""
    skip_suffixes = {".safetensors"}
    skip_names    = {"tokenizer.json", "config.json", "model.safetensors.index.json"}
    for p in src.iterdir():
        if p.is_dir():
            continue
        if p.suffix in skip_suffixes or p.name in skip_names:
            continue
        target = dst / p.name
        if not target.exists():
            shutil.copy2(p, target)
            print(f"  copied: {p.name}")


def extend_embeddings_streaming(src: Path, dst: Path, old_vocab: int, new_vocab: int):
    """
    safetensors シャードを直接読み書きして embed_tokens / lm_head だけを拡張。
    モデル全体をメモリに乗せないため大規模モデル（32B+）でも動作する。
    新トークンの初期ベクトルは既存語彙の平均で初期化。
    """
    import numpy as np
    from safetensors import safe_open
    from safetensors.numpy import save_file

    n_new = new_vocab - old_vocab
    if n_new <= 0:
        print(f"  new_vocab ({new_vocab}) <= old_vocab ({old_vocab}), コピーのみ")
        import shutil
        for p in src.iterdir():
            if p.suffix in (".safetensors",) or p.name == "model.safetensors.index.json":
                shutil.copy2(p, dst / p.name)
        return

    index_file = src / "model.safetensors.index.json"
    if not index_file.exists():
        raise FileNotFoundError(f"index.json が見つかりません: {index_file}\n"
                                "シングルファイルモデルは対応していません（シャード形式のみ）")

    with open(index_file, encoding="utf-8") as f:
        index = json.load(f)
    weight_map = index["weight_map"]

    EMBED_KEY   = "model.embed_tokens.weight"
    LM_HEAD_KEY = "lm_head.weight"

    embed_shard   = weight_map.get(EMBED_KEY)
    lm_head_shard = weight_map.get(LM_HEAD_KEY)
    modified_shards = {s for s in (embed_shard, lm_head_shard) if s}

    all_shards = sorted(set(weight_map.values()))
    print(f"\n  Shards: {len(all_shards)}個、変更対象: {modified_shards}")

    import shutil
    for shard_name in all_shards:
        src_path = src / shard_name
        dst_path = dst / shard_name

        if shard_name not in modified_shards:
            print(f"  copy: {shard_name}")
            shutil.copy2(src_path, dst_path)
            continue

        print(f"  extend: {shard_name}")
        tensors = {}
        with safe_open(str(src_path), framework="numpy") as f:
            for key in f.keys():
                tensors[key] = f.get_tensor(key)

        if EMBED_KEY in tensors:
            emb = tensors[EMBED_KEY]           # [old_vocab, dim]
            if emb.shape[0] == old_vocab:
                mean_vec = emb.mean(axis=0, keepdims=True)   # [1, dim]
                new_rows = np.broadcast_to(mean_vec, (n_new, emb.shape[1])).copy()
                tensors[EMBED_KEY] = np.concatenate([emb, new_rows], axis=0)
                print(f"    embed_tokens: {old_vocab} → {new_vocab}  (dim={emb.shape[1]})")

        if LM_HEAD_KEY in tensors:
            lm = tensors[LM_HEAD_KEY]
            if lm.shape[0] == old_vocab:
                lm_mean = lm.mean(axis=0, keepdims=True)
                new_rows = np.broadcast_to(lm_mean, (n_new, lm.shape[1])).copy()
                tensors[LM_HEAD_KEY] = np.concatenate([lm, new_rows], axis=0)
                print(f"    lm_head: {old_vocab} → {new_vocab}")
            elif lm.shape[1] == old_vocab:
                lm_mean = lm.mean(axis=1, keepdims=True)
                new_cols = np.broadcast_to(lm_mean, (lm.shape[0], n_new)).copy()
                tensors[LM_HEAD_KEY] = np.concatenate([lm, new_cols], axis=1)
                print(f"    lm_head (transposed): {old_vocab} → {new_vocab}")

        save_file(tensors, str(dst_path))

    # index.json もコピー（weight_map は変更不要、vocab変更は config.json で反映済み）
    shutil.copy2(index_file, dst / "model.safetensors.index.json")
    print(f"  全シャード保存完了: {dst}")


def verify_tokens(dst: Path, tokens: list[str]):
    """追加されたトークンのIDを検証して表示。"""
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(dst / "tokenizer.json"))
    print("\n--- verify ---")
    all_ok = True
    for t in tokens:
        tid = tok.token_to_id(t)
        if tid is None:
            print(f"  ✗ {t!r} → NOT FOUND")
            all_ok = False
        else:
            print(f"  ✓ {t!r} → [{tid}]")
    if all_ok:
        print("ALL OK")
    return all_ok


def main():
    print("=" * 50)
    print("  Tokenizer Extension  v3")
    print("  (Qwen3-32B + IDS12 + <解説> トークン)")
    print("=" * 50)
    print(f"  Source: {BASE_DIR}")
    print(f"  Output: {OUT_DIR}")
    print(f"  Tokens: {len(NEW_TOKENS)} 個")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    copy_other_files(BASE_DIR, OUT_DIR)

    print("\n[1] Extending tokenizer...")
    _, new_vocab_size = extend_tokenizer_json(
        BASE_DIR / "tokenizer.json",
        OUT_DIR,
        NEW_TOKENS,
    )

    extend_tokenizer_config(BASE_DIR, OUT_DIR, NEW_TOKENS)

    print("\n[2] Updating config...")
    extend_config(BASE_DIR, OUT_DIR, new_vocab_size)

    print("\n[3] Extending model embeddings (streaming, shard-by-shard)...")
    old_vocab = 151936   # Qwen3-32B デフォルト（Qwen3 シリーズ共通 vocab_size）
    extend_embeddings_streaming(BASE_DIR, OUT_DIR, old_vocab, new_vocab_size)

    print(f"\n完了: {OUT_DIR}")
    print(f"  追加トークン数: {len(NEW_TOKENS)}")
    print(f"  新 vocab_size: {new_vocab_size}")

    verify_tokens(OUT_DIR, NEW_TOKENS)

    print("\n次のステップ: prepare_finetune.py → run_finetune.sh")


if __name__ == "__main__":
    main()
