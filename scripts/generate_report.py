#!/usr/bin/env python3
"""
generate_report.py
IDS Symbol Renderer — 開発ログ・試行錯誤記録 PDF 生成
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
import datetime

# ── フォント登録 ──────────────────────────────────────────────────────────────
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
FONT_SANS = 'HeiseiKakuGo-W5'
FONT_SERIF = 'HeiseiMin-W3'

# ── スタイル定義 ──────────────────────────────────────────────────────────────
def make_styles():
    s = {}
    base = dict(fontName=FONT_SANS, leading=16)

    s['title'] = ParagraphStyle('title',
        fontName=FONT_SANS, fontSize=22, leading=30,
        textColor=colors.HexColor('#1a1a2e'), spaceAfter=6, alignment=TA_CENTER)

    s['subtitle'] = ParagraphStyle('subtitle',
        fontName=FONT_SANS, fontSize=12, leading=18,
        textColor=colors.HexColor('#4a4a6a'), spaceAfter=4, alignment=TA_CENTER)

    s['date'] = ParagraphStyle('date',
        fontName=FONT_SANS, fontSize=10, leading=14,
        textColor=colors.HexColor('#888888'), spaceAfter=20, alignment=TA_CENTER)

    s['h1'] = ParagraphStyle('h1',
        fontName=FONT_SANS, fontSize=16, leading=22,
        textColor=colors.HexColor('#1a1a2e'),
        spaceBefore=18, spaceAfter=8,
        borderPad=4, borderWidth=0,
        leftIndent=0)

    s['h2'] = ParagraphStyle('h2',
        fontName=FONT_SANS, fontSize=13, leading=18,
        textColor=colors.HexColor('#2d2d5e'),
        spaceBefore=14, spaceAfter=6)

    s['h3'] = ParagraphStyle('h3',
        fontName=FONT_SANS, fontSize=11, leading=16,
        textColor=colors.HexColor('#444466'),
        spaceBefore=10, spaceAfter=4)

    s['body'] = ParagraphStyle('body',
        fontName=FONT_SANS, fontSize=9.5, leading=15,
        textColor=colors.HexColor('#333333'),
        spaceAfter=6, alignment=TA_JUSTIFY)

    s['bullet'] = ParagraphStyle('bullet',
        fontName=FONT_SANS, fontSize=9.5, leading=15,
        textColor=colors.HexColor('#333333'),
        leftIndent=12, spaceAfter=3,
        bulletIndent=4)

    s['code'] = ParagraphStyle('code',
        fontName='Courier', fontSize=8.5, leading=13,
        textColor=colors.HexColor('#1a1a1a'),
        backColor=colors.HexColor('#f5f5f5'),
        borderPad=6, spaceAfter=8,
        leftIndent=8)

    s['note'] = ParagraphStyle('note',
        fontName=FONT_SANS, fontSize=9, leading=14,
        textColor=colors.HexColor('#555577'),
        backColor=colors.HexColor('#eef0ff'),
        borderPad=5, leftIndent=8, spaceAfter=8)

    s['error'] = ParagraphStyle('error',
        fontName=FONT_SANS, fontSize=9, leading=14,
        textColor=colors.HexColor('#cc2200'),
        backColor=colors.HexColor('#fff0ee'),
        borderPad=5, leftIndent=8, spaceAfter=8)

    s['success'] = ParagraphStyle('success',
        fontName=FONT_SANS, fontSize=9, leading=14,
        textColor=colors.HexColor('#006633'),
        backColor=colors.HexColor('#efffee'),
        borderPad=5, leftIndent=8, spaceAfter=8)

    s['caption'] = ParagraphStyle('caption',
        fontName=FONT_SANS, fontSize=8.5, leading=13,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER, spaceAfter=6)

    return s

def H1(text, s): return Paragraph(f'<b>{text}</b>', s['h1'])
def H2(text, s): return Paragraph(f'<b>{text}</b>', s['h2'])
def H3(text, s): return Paragraph(f'<b>{text}</b>', s['h3'])
def P(text, s):  return Paragraph(text, s['body'])
def B(text, s):  return Paragraph(f'• {text}', s['bullet'])
def SP(n=6):     return Spacer(1, n)
def HR():        return HRFlowable(width='100%', thickness=0.5,
                                    color=colors.HexColor('#cccccc'), spaceAfter=6)

def section_header(title, s):
    return [
        SP(4),
        HRFlowable(width='100%', thickness=2, color=colors.HexColor('#2d2d5e'), spaceAfter=4),
        Paragraph(f'<b>{title}</b>', s['h1']),
        SP(2),
    ]

def table_2col(data, s, col_widths=None):
    if col_widths is None:
        col_widths = [55*mm, 105*mm]
    rows = [[Paragraph(f'<b>{k}</b>', s['body']), Paragraph(v, s['body'])] for k, v in data]
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f0f0f8')),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cccccc')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    return t

def metrics_table(headers, rows, s):
    all_rows = [[Paragraph(f'<b>{h}</b>', s['body']) for h in headers]]
    for row in rows:
        all_rows.append([Paragraph(str(c), s['body']) for c in row])
    col_w = [160*mm / len(headers)] * len(headers)
    t = Table(all_rows, colWidths=col_w)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2d2d5e')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#fafafa')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1),
         [colors.HexColor('#fafafa'), colors.HexColor('#f0f0f8')]),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cccccc')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    return t

# ── コンテンツ構築 ─────────────────────────────────────────────────────────────
def build_content(s):
    story = []

    # ── 表紙 ──────────────────────────────────────────────────────────────────
    story += [
        SP(40),
        Paragraph('IDS Symbol Renderer', s['title']),
        Paragraph('AI ファインチューニング 開発記録', s['subtitle']),
        Paragraph('設計・試行錯誤・改善の経緯', s['subtitle']),
        SP(8),
        HRFlowable(width='60%', thickness=1.5,
                   color=colors.HexColor('#2d2d5e'), spaceAfter=8),
        SP(4),
        Paragraph(f'作成日: {datetime.date.today().strftime("%Y年%m月%d日")}', s['date']),
        PageBreak(),
    ]

    # ── 目次 ──────────────────────────────────────────────────────────────────
    story += section_header('目次', s)
    toc_items = [
        ('1', 'プロジェクト概要'),
        ('2', 'システムアーキテクチャ'),
        ('3', 'データ構造と品質管理'),
        ('4', '自動解析システム（AutoResearch）'),
        ('5', 'ファインチューニング — v1（初回）'),
        ('6', 'ファインチューニング — v2（データ拡充）'),
        ('7', 'ファインチューニング — v3（CoT + 特殊トークン）'),
        ('8', 'トークナイザー拡張の試行錯誤'),
        ('9', '推論品質の問題と改善'),
        ('10', '現在の設定と残課題'),
    ]
    for num, title in toc_items:
        story.append(Paragraph(f'&nbsp;&nbsp;<b>{num}.</b>&nbsp; {title}', s['body']))
        story.append(SP(3))
    story.append(PageBreak())

    # ── §1 プロジェクト概要 ─────────────────────────────────────────────────
    story += section_header('1. プロジェクト概要', s)
    story += [
        P('IDS Symbol Renderer は、作者が漢字の筆画を組み合わせて抽象的な記号（シンボル）を制作・管理するWebアプリケーションである。'
          '漢字の一部の筆画を除去し、複数の漢字を重ねたり並べたりすることで、具体的な言葉の意味から離れた視覚的なシンボルを生成する。', s),
        SP(4),
        H2('1.1 制作の基本思想', s),
        P('テーマ（お題）に対して漢字を選び、IDS（Ideographic Description Sequences）の構造的な考え方を応用して空間的に配置する。'
          '単に漢字の意味を借りるのではなく、<b>テーマを抽象概念として捉え直し</b>、その概念を漢字の形・画数・配置によって視覚化する。', s),
        SP(4),
        H2('1.2 技術スタック', s),
        table_2col([
            ('フロントエンド', 'Vite + Vanilla JS、SVG レンダリング'),
            ('バックエンド', 'Vite Dev Server (Node.js) + Python スクリプト群'),
            ('AI モデル', 'Qwen3-4B（MLX-LM、Apple Silicon）'),
            ('学習環境', 'mlx_lm.lora / mlx_lm.fuse（M3 Max MacBook）'),
            ('データ形式', 'JSONL（results / ai_results / hybrid_results）'),
        ], s),
        PageBreak(),
    ]

    # ── §2 システムアーキテクチャ ────────────────────────────────────────────
    story += section_header('2. システムアーキテクチャ', s)
    story += [
        H2('2.1 ファイル構成（主要）', s),
        table_2col([
            ('vite.config.js', 'メインサーバー設定。/api/generate・/api/research・/api/score 等のエンドポイントを定義'),
            ('gallery.html', 'ギャラリーUI。作品閲覧・採点・AI提案・研究パネル'),
            ('scripts/auto_research.py', '自動パターン解析（k-means クラスタリング + ルールベース分類）'),
            ('scripts/prepare_finetune.py', '学習データ生成（Format A〜E）'),
            ('scripts/extend_tokenizer.py', 'トークナイザー拡張（特殊トークン追加）'),
            ('scripts/run_finetune.sh', 'ファインチューニングパイプライン'),
            ('scripts/start_mlx_server.sh', 'MLX 推論サーバー起動'),
            ('models/Qwen3-4B/', 'ベースモデル（約7GB、HuggingFace からDL）'),
            ('models/Qwen3-4B-extended/', '特殊トークン追加済みモデル'),
            ('models/qwen3-4b-ids-fused/', '学習済み推論モデル（現行）'),
            ('results.jsonl', '手作り作品データ'),
            ('ai_results.jsonl', 'AI提案作品データ'),
            ('hybrid_results.jsonl', 'AI提案を作者が修正した作品データ'),
            ('scores.json', 'G（グラフィック）/ A（抽象化）採点記録'),
            ('research/patterns.json', '解析結果（パターン分類 + クラスタ発見）'),
        ], s),
        SP(6),
        H2('2.2 データフロー', s),
        P('① 作者がお題を入力 → ② AI提案（/api/generate）→ ③ 作者が修正・採用 → '
          '④ 保存（results.jsonl）→ ⑤ 採点（scores.json）→ ⑥ 定期的に auto_research.py を実行してパターン発見 '
          '→ ⑦ パターンデータを学習データに反映 → ⑧ 再ファインチューニング', s),
        PageBreak(),
    ]

    # ── §3 データ構造と品質管理 ──────────────────────────────────────────────
    story += section_header('3. データ構造と品質管理', s)
    story += [
        H2('3.1 レコード形式', s),
        Paragraph('<font name="Courier" size="8">{'
                  '"theme": "お題", "interpretation": "制作意図", '
                  '"instances": [{"char": "漢字", "removedIndices": [0,1], '
                  '"transform": {"tx": 0, "ty": 0, "scaleX": 1, "scaleY": 1, "rotate": 0}}], '
                  '"_source": "human|ai|hybrid"}</font>', s['code']),
        SP(4),
        H2('3.2 品質スコア', s),
        P('各記録は <b>G（グラフィック）スコア</b> と <b>A（抽象化）スコア</b> の2軸で 0〜9 点で採点される。'
          'ファインチューニング学習データへの採用基準:', s),
        B('手作り・hybrid: すべて採用', s),
        B('AI生成: G + A ≥ 10 のみ採用', s),
        B('高品質（G + A ≥ 14）: Format A を 3× 重複してデータ強化', s),
        SP(4),
        H2('3.3 interpretation（制作意図）の重要性', s),
        P('interpretation フィールドは、なぜその漢字を選んだか・どのように抽象化したかを記述する。'
          'このフィールドが充実しているほど、AI が<b>意味的な抽象化プロセス</b>を学習できる。'
          '文字数 ≥ 20 のレコードを Format E（ChainOfThought）学習データの材料として使用。', s),
        PageBreak(),
    ]

    # ── §4 AutoResearch ──────────────────────────────────────────────────────
    story += section_header('4. 自動解析システム（AutoResearch）', s)
    story += [
        H2('4.1 目的と背景', s),
        P('既存のIDS分類（二字重畳・二字相補・三字組等）に当てはまらない独自の構造パターンを自動発見するために実装。'
          'ルールベース分類に加え、k-means クラスタリングにより未知パターンを検出する。', s),
        SP(4),
        H2('4.2 特徴ベクトル（37次元）', s),
        table_2col([
            ('位置・スケール', 'tx / ty / scaleX / scaleY（各インスタンス × 最大4）'),
            ('除去率', 'removedIndices / totalStrokes per instance'),
            ('偏り指標', 'early_bias（前半画の除去傾向）/ late_bias（後半画の除去傾向）'),
            ('回転', 'rotate（度）'),
            ('ペア間距離', '重心間ユークリッド距離'),
            ('包含スコア', '一方が他方のBBox内に入る程度'),
            ('スケール対比', '大きい方 / 小さい方のスケール比'),
        ], s),
        SP(4),
        H2('4.3 novelty_score', s),
        P('各クラスタの novelty_score = 1.0 − (支配的ルールカテゴリの割合)。'
          '複数のルールカテゴリが混在するクラスタほど高スコアとなり、既存分類に収まらない新規構造として報告される。', s),
        SP(4),
        H2('4.4 record_ids の記録', s),
        P('各パターン・クラスタに属するレコードIDを patterns.json に保存し、ギャラリーUIでクリックするとそのクラスタの作品だけを表示できる機能を実装。', s),
        PageBreak(),
    ]

    # ── §5 ファインチューニング v1 ────────────────────────────────────────────
    story += section_header('5. ファインチューニング v1（初回）', s)
    story += [
        H2('5.1 概要', s),
        P('最初のファインチューニングは「お題→JSON生成」の基本形式のみ。'
          'Qwen3-4B を MLX-LM の full fine-tune で学習。', s),
        SP(4),
        H2('5.2 発生した問題', s),
        Paragraph('【問題1】 --num-epochs オプションが存在しない', s['error']),
        P('mlx_lm.lora には --num-epochs が存在せず、--iters で指定する必要がある。'
          '→ iters = train_count × 5 に修正。', s),
        Paragraph('【問題2】 --lr-schedule cosine_decay が無効', s['error']),
        P('このオプションも存在しないため削除。', s),
        Paragraph('【問題3】 --de-quantize が無効（mlx_lm.fuse）', s['error']),
        P('正しくは --dequantize（ハイフンなし）。', s),
        Paragraph('【問題4】 fused モデルが空', s['error']),
        P('mlx_lm.fuse がエラーで終了し qwen3-4b-ids-fused/ が空のままになった。手動で正しいコマンドを実行して修正。', s),
        SP(4),
        H2('5.3 学習結果', s),
        metrics_table(
            ['指標', '値'],
            [
                ['Train loss', '0.028'],
                ['Val loss', '0.071'],
                ['データ数', '333 train / 37 valid'],
                ['判定', '軽度の過学習（val > train の差が大きい）'],
            ], s),
        PageBreak(),
    ]

    # ── §6 ファインチューニング v2 ────────────────────────────────────────────
    story += section_header('6. ファインチューニング v2（データ拡充）', s)
    story += [
        H2('6.1 改善内容', s),
        B('学習フォーマット A〜D の4種類を導入', s),
        B('Format A: お題→生成（メイン、267件）', s),
        B('Format B: 記号JSON→構造と意味の解説（67件）', s),
        B('Format C: 構造パターン問答（36件）', s),
        B('Format D: 創作哲学問答（6件）', s),
        SP(4),
        H2('6.2 推論時プロンプトとの不一致問題', s),
        Paragraph('【根本原因】 学習データに ## 参考作品 ブロックがないのに推論時は参照例を含めていた', s['error']),
        P('学習では参照例なしのフォーマットで訓練したが、推論時はギャラリーの過去作品を ## 参考作品 として送っていた。'
          'モデルは参照例の座標値を<b>そのまま出力</b>するようになった（記憶の単純コピー）。'
          '→ 推論プロンプトから ## 参考作品 を完全に削除して解決。', s),
        SP(4),
        H2('6.3 Format C の英語タグ問題', s),
        Paragraph('【問題】 pattern[\'name\'] が英語タグ名のまま出力される', s['error']),
        P('patterns.json の name フィールドが英語タグ名（dual_overlap など）だった場合に'
          '「dual_overlapは、dual_overlapパターン...」という奇妙な文が生成された。'
          '→ TAG_LABELS 辞書による日本語変換 + FALLBACK_DESCS による説明文を追加。', s),
        SP(4),
        H2('6.4 学習結果', s),
        metrics_table(
            ['指標', '値'],
            [
                ['Train loss', '0.028'],
                ['Val loss', '0.071'],
                ['データ数', '370件 → 333 train / 37 valid'],
                ['改善', 'AI提案がコピーから脱却、独自の提案が出るようになった'],
            ], s),
        PageBreak(),
    ]

    # ── §7 ファインチューニング v3 ────────────────────────────────────────────
    story += section_header('7. ファインチューニング v3（CoT + 特殊トークン）', s)
    story += [
        H2('7.1 設計思想', s),
        P('「テーマを直接記号化するのではなく、テーマを<b>抽象化する推論過程</b>を学習させたい」'
          'という問題意識から、ChainOfThought（CoT）形式と構造パターンの特殊トークンを導入。', s),
        SP(4),
        H2('7.2 追加した特殊トークン（15個）', s),
        table_2col([
            ('思考ステップ（5個）',
             '&lt;思考&gt; &lt;/思考&gt; &lt;概念&gt; &lt;選択&gt; &lt;構造&gt;'),
            ('IDS構造タグ（10個）',
             '&lt;単漢字除去&gt; &lt;単漢字&gt; &lt;二字重畳&gt; &lt;二字相補&gt; '
             '&lt;二字横並&gt; &lt;二字縦積&gt; &lt;三字組&gt; '
             '&lt;同字重畳&gt; &lt;同字並列&gt; &lt;多漢字&gt;'),
        ], s),
        SP(4),
        H2('7.3 Format E（ChainOfThought）', s),
        P('interpretation が20文字以上のレコード（62件）に対して以下の形式で訓練データを生成:', s),
        Paragraph(
            '<font name="Courier" size="8">'
            '&lt;思考&gt;\n'
            '&lt;概念&gt; 「走り続けている」を「不断の前進、止まらない意志」として捉える\n'
            '&lt;選択&gt; 走・続：走の動きと続の連続性が概念を体現する\n'
            '&lt;構造&gt; &lt;二字重畳&gt; 二字を重ねて動きの持続を表す重畳構造を採用\n'
            '&lt;/思考&gt;\n'
            '{"interpretation": "...", "instances": [...]}'
            '</font>', s['code']),
        SP(4),
        H2('7.4 品質重み付け', s),
        P('G + A ≥ 14 の高品質レコードは Format A データを 3× 重複させてサンプリング強度を上げた。', s),
        SP(4),
        H2('7.5 学習結果', s),
        metrics_table(
            ['指標', '値'],
            [
                ['手法', 'LoRA（full fine-tune から変更）'],
                ['LoRA rank', '16、alpha 32、dropout 0.05'],
                ['対象層', '後半 16 層'],
                ['学習速度', '0.030 it/sec（full）→ 0.298 it/sec（LoRA）10× 改善'],
                ['ピークメモリ', '24.5 GB（full）→ 11.3 GB（LoRA）'],
                ['学習時間', '約 2 時間'],
                ['最終 Val loss', '0.063（v2: 0.071 より改善）'],
                ['最終 Train loss', '0.022'],
                ['学習トークン数', '3,014,300'],
                ['データ数', '454件 → 408 train / 46 valid'],
            ], s),
        PageBreak(),
    ]

    # ── §8 トークナイザー拡張の試行錯誤 ──────────────────────────────────────
    story += section_header('8. トークナイザー拡張の試行錯誤', s)
    story += [
        P('extend_tokenizer.py の開発では多数の問題が連鎖して発生した。各問題と解決策を記録する。', s),
        SP(6),

        Paragraph('【問題1】 copy_other_files がディレクトリをコピーしてクラッシュ', s['error']),
        P('Qwen3-4B/.cache がディレクトリだったため shutil.copy2 でエラー。→ p.is_dir() チェックを追加。', s),
        SP(4),

        Paragraph('【問題2】 新トークンIDが既存 added_tokens と衝突', s['error']),
        P('next_id = max(BPE vocab) + 1 = 151643 から開始したが、Qwen3 の added_tokens が'
          '151643〜151668 を使用中。→ max(全IDの最大値) + 1 から開始するよう修正。'
          '結果、新トークンは 151669〜151683 に割り当て。', s),
        SP(4),

        Paragraph('【問題3】 config.json の vocab_size を縮小してしまい embedding と不整合', s['error']),
        P('new_vocab_size = 151684 < モデル embedding 行数 151936。→ max(new, old) で縮小しないよう修正。', s),
        SP(4),

        Paragraph('【問題4】 model.safetensors が保存されず学習がクラッシュ', s['error']),
        P('n_new ≤ 0（拡張不要）の早期リターン時にモデル保存をスキップ。'
          '→ 常に safetensors を保存するよう修正。', s),
        SP(4),

        Paragraph('【問題5】 model.safetensors.index.json がシャード参照で競合', s['error']),
        P('元モデルのシャードインデックスがコピーされ、単一 model.safetensors と競合。'
          '→ copy_other_files のスキップリストに追加。', s),
        SP(4),

        Paragraph('【問題6】 tokenizer.json の手動 JSON 操作で Rust パーサーエラー', s['error']),
        P('tokenizer.json を json.dump で再シリアライズすると line 757615 で'
          '"expected , or }" エラー。BPE vocab への直接追加が原因。'
          '→ tokenizers ライブラリの Tokenizer.add_special_tokens() に変更。', s),
        SP(4),

        Paragraph('【問題7】 AutoTokenizer が特殊トークンを単一IDにエンコードしない', s['error']),
        P('tokenizers ライブラリでは [151669] と正しくエンコードされるが、'
          'mlx_lm が使う AutoTokenizer（Qwen2Tokenizer スロートークナイザー）が'
          'tokenizer.json の added_tokens を無視。'
          '→ tokenizer_config.json の additional_special_tokens にも追加して解決。', s),
        SP(4),

        Paragraph('【問題8】 mlx_lm.fuse が extended tokenizer を保持しない', s['error']),
        P('fuse コマンドがベースモデルの tokenizer_config を使うため、'
          'fused モデルの additional_special_tokens が空になる。'
          '→ fuse 後に extended の tokenizer ファイルを上書きコピーするステップを追加。', s),
        PageBreak(),
    ]

    # ── §9 推論品質の問題と改善 ──────────────────────────────────────────────
    story += section_header('9. 推論品質の問題と改善', s)
    story += [
        H2('9.1 AI提案がデータのコピーになっていた問題', s),
        Paragraph('【症状】 tx: -43.42 など学習データの座標値が完全一致で出力される', s['error']),
        P('【原因】 推論プロンプトに ## 参考作品 として学習データの座標値付き JSON を含めていたため、'
          'モデルが「例を見てコピーする」行動を学習した。'
          '【解決】 参照例を推論プロンプトから完全除去。', s),
        SP(4),
        H2('9.2 CoT プロンプトが機能しなかった問題', s),
        Paragraph('【症状】 ユーザープロンプトに &lt;思考&gt; タグを含めるとゴミ文字が出力される', s['error']),
        P('【原因】 Format E の訓練はユーザープロンプトが Format A と同一で、'
          'アシスタント側が &lt;思考&gt; を出力する形式。'
          'ユーザー側に &lt;思考&gt; を書くフォーマットは学習データに存在しないため混乱。'
          '【解決】 元のユーザープロンプト形式に戻し、JSON 前のフリーテキストを interpretation として抽出。', s),
        SP(4),
        H2('9.3 interpretation が常にデフォルト文になる問題', s),
        Paragraph('【症状】 「お題「X」を漢字の組み合わせで表現した」という空虚な interpretation', s['error']),
        P('【原因】 学習データ（Format A）の多くが interpretation なしのレコードで、'
          'デフォルト文でフォールバックしていた。モデルがこのパターンを強く学習。', s),
        P('【解決策】 応答テキストのパース改善: (1) &lt;思考&gt; ブロックから概念・選択理由を抽出、'
          '(2) それもなければ JSON前のフリーテキスト（日本語比率フィルタ付き）を抽出して補完。', s),
        SP(4),
        H2('9.4 LLM未使用メッセージの問題', s),
        P('研究パネルの「再解析」ボタンが MLX サーバー未起動時に「LLM未使用」と表示。'
          '→ ボタン押下時に /api/mlx-status を確認し、未起動なら自動起動して 60秒ポーリング待機するよう修正。', s),
        PageBreak(),
    ]

    # ── §10 現在の設定と残課題 ──────────────────────────────────────────────
    story += section_header('10. 現在の設定と残課題', s)
    story += [
        H2('10.1 現在の稼働設定', s),
        metrics_table(
            ['項目', '設定値'],
            [
                ['ベースモデル', 'Qwen3-4B（151936 vocab）'],
                ['拡張モデル', 'Qwen3-4B-extended（+ 特殊トークン 15個）'],
                ['推論モデル', 'qwen3-4b-ids-fused（LoRA fused）'],
                ['MLXサーバー', 'localhost:11435、temp=0.8、top-p=0.95、top-k=60'],
                ['学習手法', 'LoRA rank=16、後半16層、lr=2e-4'],
                ['学習データ', '454件（A:283, B:67, C:36, D:6, E:62）'],
            ], s),
        SP(6),
        H2('10.2 特殊トークンの現状', s),
        P('新トークン（151669〜151683）はQwen3の予約済み空間内に収まっており、'
          'embedding 行数の拡張は不要だった。ただし、この空間の embedding ベクトルは'
          '元モデルで未学習のためランダム初期化状態。LoRA 学習によって更新されたが、'
          '<b>mean 初期化よりも収束が遅い可能性がある</b>。', s),
        SP(4),
        H2('10.3 残課題と改善方針', s),

        H3('（1）interpretation の質向上（最優先）', s),
        P('現状のモデルが漢字選択の理由を十分に言語化できていない根本原因は、'
          '学習データの interpretation フィールドが薄いこと。'
          '今後の作品制作時に interpretation を詳しく記述することで次回学習を改善できる。', s),

        H3('（2）Format E の比率向上', s),
        P('現在 Format E は 62件 / 454件 = 13.7%。CoT 形式の学習比率が低いため、'
          'モデルが &lt;思考&gt; 形式を自発的に出力しにくい。'
          'interpretation が充実した記録が増えれば Format E の件数も増加する。', s),

        H3('（3）mean 初期化の実施', s),
        P('新トークン（ID 151669〜151683）の embedding を既存語彙の平均ベクトルで初期化してから'
          '再学習することで収束を安定化できる。', s),

        H3('（4）過学習の監視', s),
        P('val loss 0.063 / train loss 0.022 の差（0.041）は許容範囲内だが、'
          'データが増えた場合は eval 頻度を上げて過学習を早期検知することが望ましい。', s),

        H3('（5）full fine-tune の再検討', s),
        P('LoRA は高速だが、特殊トークンの embedding 学習には full fine-tune の方が効果的な場合がある。'
          '十分な時間を確保できる場合（夜間等）に full fine-tune を試す価値がある。', s),
        SP(10),
        HRFlowable(width='100%', thickness=1, color=colors.HexColor('#cccccc'), spaceAfter=6),
        Paragraph(f'本書は IDS Symbol Renderer の AI ファインチューニング開発記録として作成された。'
                  f'作成日: {datetime.date.today().strftime("%Y年%m月%d日")}', s['caption']),
    ]

    return story


# ── メイン ─────────────────────────────────────────────────────────────────────
def main():
    import os
    out_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'IDS_Symbol_Renderer_開発記録.pdf'
    )
    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm,
        topMargin=22*mm, bottomMargin=22*mm,
        title='IDS Symbol Renderer 開発記録',
        author='IDS Symbol Renderer Project',
    )
    s = make_styles()
    story = build_content(s)
    doc.build(story)
    print(f'PDF 生成完了: {out_path}')


if __name__ == '__main__':
    main()
