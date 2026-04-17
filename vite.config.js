import { defineConfig } from 'vite'
import fs from 'fs'
import path from 'path'
import { spawn } from 'child_process'
import http from 'http'

// ===== MLX サーバー管理 =====
let mlxProc = null

function checkMlxReady(cb) {
  const req = http.get('http://localhost:11435/v1/models', res => {
    cb(res.statusCode === 200)
    res.resume()
  })
  req.on('error', () => cb(false))
  req.setTimeout(1500, () => { req.destroy(); cb(false) })
}

// .env を手動ロード（dotenv未使用）
const envPath = path.resolve('.env')
if (fs.existsSync(envPath)) {
  fs.readFileSync(envPath, 'utf8').split('\n').forEach(line => {
    const m = line.match(/^([^#=]+)=(.*)$/)
    if (m) process.env[m[1].trim()] = m[2].trim()
  })
}

export default defineConfig({
  plugins: [
    {
      name: 'save-results',
      configureServer(server) {
        // 利用可能な漢字コード一覧を返す
        server.middlewares.use('/api/kanji-codes', (req, res) => {
          try {
            const dir = path.resolve('public/data/kanjivg')
            const files = fs.readdirSync(dir)
            const codes = files
              .map(f => f.match(/^kanji_([0-9a-f]{5})\.svg$/i)?.[1])
              .filter(Boolean)
            res.setHeader('Content-Type', 'application/json')
            res.end(JSON.stringify(codes))
          } catch (e) {
            res.statusCode = 500
            res.end(JSON.stringify({ error: e.message }))
          }
        })

        server.middlewares.use('/api/count', (req, res) => {
          try {
            const url = new URL(req.url, 'http://localhost')
            const theme = url.searchParams.get('theme') || ''
            const countFile = (filePath) => {
              if (!fs.existsSync(filePath)) return 0
              return fs.readFileSync(filePath, 'utf8').split('\n').filter(Boolean).filter(line => {
                try { return JSON.parse(line).theme === theme } catch { return false }
              }).length
            }
            const count = countFile(path.resolve('results.jsonl'))
            res.setHeader('Content-Type', 'application/json')
            res.end(JSON.stringify({ count }))
          } catch (e) {
            res.statusCode = 500
            res.end(JSON.stringify({ error: e.message }))
          }
        })

        server.middlewares.use('/api/results', (req, res) => {
          try {
            const readJSONL = (filePath, source) => {
              if (!fs.existsSync(filePath)) return []
              return fs.readFileSync(filePath, 'utf8')
                .split('\n').filter(Boolean)
                .map(l => { try { const r = JSON.parse(l); r.source = source; return r } catch { return null } })
                .filter(Boolean)
            }
            const humanRecords  = readJSONL(path.resolve('results.jsonl'), 'human')
            const aiRecords     = readJSONL(path.resolve('ai_results.jsonl'), 'ai')
            const hybridRecords = readJSONL(path.resolve('hybrid_results.jsonl'), 'hybrid')
            const records = [...humanRecords, ...aiRecords, ...hybridRecords]
            // scores.json はAI・hybridレコードに適用
            const scoresPath = path.resolve('scores.json')
            if (fs.existsSync(scoresPath)) {
              const scores = JSON.parse(fs.readFileSync(scoresPath, 'utf8'))
              records.forEach(r => {
                if (r.source !== 'human') { const k = r.symbol_id || r.timestamp; if (k && scores[k]) r.score = scores[k] }
              })
            }
            res.setHeader('Content-Type', 'application/json')
            res.end(JSON.stringify(records))
          } catch (e) {
            res.statusCode = 500
            res.end(JSON.stringify({ error: e.message }))
          }
        })

        server.middlewares.use('/api/generate', async (req, res) => {
          if (req.method !== 'POST') { res.statusCode = 405; res.end(); return }
          let body = ''
          req.on('data', chunk => { body += chunk })
          req.on('end', async () => {
            try {
              const { theme } = JSON.parse(body)

              // ===== 全漢字コードをマップ化（char → code）=====
              const kanjiDir = path.resolve('public/data/kanjivg')
              const allCodes = fs.readdirSync(kanjiDir)
                .map(f => f.match(/^kanji_([0-9a-f]{5})\.svg$/i)?.[1])
                .filter(Boolean)
              const charToCode = new Map()
              for (const code of allCodes) {
                const char = String.fromCodePoint(parseInt(code, 16))
                charToCode.set(char, code)
              }

              // ===== データ読み込み =====
              const readJSONL = (filePath, source) => {
                if (!fs.existsSync(filePath)) return []
                return fs.readFileSync(filePath, 'utf8').split('\n').filter(Boolean)
                  .map(l => { try { const r = JSON.parse(l); r.source = source; return r } catch { return null } })
                  .filter(Boolean)
              }
              const humanRecords  = readJSONL(path.resolve('results.jsonl'), 'human')
              const aiRecords     = readJSONL(path.resolve('ai_results.jsonl'), 'ai')
              const hybridRecords = readJSONL(path.resolve('hybrid_results.jsonl'), 'hybrid')
              const records = [...humanRecords, ...aiRecords, ...hybridRecords]
              // scores.json はAI・hybridレコードに適用
              const scoresPath = path.resolve('scores.json')
              if (fs.existsSync(scoresPath)) {
                const scores = JSON.parse(fs.readFileSync(scoresPath, 'utf8'))
                records.forEach(r => { if (r.source !== 'human' && r.symbol_id && scores[r.symbol_id]) r.score = scores[r.symbol_id] })
              }

              // ===== テーマ別にレコードを整理 =====
              const byThemeAll = new Map()
              for (const r of records) {
                if (!byThemeAll.has(r.theme)) byThemeAll.set(r.theme, [])
                byThemeAll.get(r.theme).push(r)
              }

              const totalScore = r =>
                r.source === 'human' ? 18
                : r.source === 'hybrid' ? (r.score ? r.score.graphic + r.score.abstraction : 16)
                : (r.score ? r.score.graphic + r.score.abstraction : -1)
              const scoreLabel = r =>
                r.source === 'human' ? ' [手作り]'
                : r.source === 'hybrid' ? (r.score ? ` [手作り+AI G${r.score.graphic} A${r.score.abstraction}]` : ' [手作り+AI]')
                : (r.score ? ` [G${r.score.graphic} A${r.score.abstraction}]` : '')

              const fmtEx = (ex, isSame) => {
                const instStr = ex.instances.map(inst => {
                  const removed = inst.strokes.filter(s => s.op === 'remove').map(s => s.index)
                  const t = inst.transform
                  const bboxStr = inst.bbox
                    ? `,"bbox":{"x":${inst.bbox.x},"y":${inst.bbox.y},"w":${inst.bbox.w},"h":${inst.bbox.h}}`
                    : ''
                  return `  {"char":"${inst.char}","totalStrokes":${inst.strokes.length},"removedIndices":[${removed}],"transform":{"tx":${t.tx},"ty":${t.ty},"scaleX":${t.scaleX ?? 1},"scaleY":${t.scaleY ?? 1}}${bboxStr}}`
                }).join(',\n')
                const overlapStr = (ex.overlap_pairs && ex.overlap_pairs.length)
                  ? `\n  ※重なり: ${ex.overlap_pairs.map(p => `${p.chars.join('↔')}=IoU${p.iou}`).join(', ')}`
                  : ''
                const sbStr = ex.symbol_bbox
                  ? `\n  ※記号フットプリント: cx=${ex.symbol_bbox.cx} cy=${ex.symbol_bbox.cy} w=${ex.symbol_bbox.w} h=${ex.symbol_bbox.h}`
                  : ''
                const interpStr = ex.interpretation ? `\n  ※解釈: ${ex.interpretation}` : ''
                const label = isSame ? `★同テーマ「${ex.theme}」` : `「${ex.theme}」`
                return `${label}${scoreLabel(ex)}:${interpStr}${sbStr}${overlapStr}\n[\n${instStr}\n]`
              }

              // スコア上位順にソート
              const sortByScore = arr => [...arr].sort((a, b) => totalScore(b) - totalScore(a))

              // ランダムな視点ヒントを選んで多様性を強制
              const perspectiveHints = [
                '動きや流れを軸に',
                '対比や矛盾を軸に',
                '余白と密度のバランスを軸に',
                '回転や反転の変換を活かして',
                '骨格だけを残す極限の除去で',
                '2字の重なりによる融合で',
                '左右非対称な構造で',
                '縦の流れを意識して',
                '一点から放射するような構造で',
                '圧縮と拡張の対比で',
              ]
              const hint = perspectiveHints[Math.floor(Math.random() * perspectiveHints.length)]

              const systemPrompt = `あなたは漢字の筆画を組み合わせて抽象的な記号を生成・解説する専門家AIです。

## キャンバス仕様
- 座標系: 109×109 SVG、中心(0, 0)基準
- tx/ty: 位置オフセット。有効範囲: -54〜54（端に近いほど見切れリスク）
- scaleX/scaleY: 拡縮倍率。1.0=原寸。推奨範囲: 0.3〜1.8（2.0以上は見切れる）
- rotate: 回転角度（度）。0・90・180・-90・±45 が視覚的に安定
- removedIndices: 除去する筆画のインデックス（0始まり）。筆画は書き順に番号付け
- 除去率: removed / totalStrokes。0.6以上=大量除去（骨格のみ残す）
- 重なり配置: 2字を同じ位置に置く場合は tx/ty の差を20以内に
- 横並び配置: tx を ±25〜45 にずらして左右に分ける
- 縦積み配置: ty を ±20〜40 にずらして上下に分ける
- スケール対比: 主役を1.0、従を0.5〜0.7 にすると主従関係が生まれる

## 記号の構造タイプ
- 単漢字・大量除去: 1字から核心的な筆画だけを残す（除去率60%以上）
- 二字重畳: 2字を中心付近に重ね、意味を融合させる
- 二字相補: 2字が前半・後半の筆画をそれぞれ担当し一体化する
- 二字横並び/縦積み: 左右または上下に分割配置
- 三字組み合わせ: 3字で空間的な三角関係を構成
- 同字反復: 同じ字を変形・ずらして重ねるか並べる
- 多漢字複合: 4字以上の複合構造

## 創造のルール
- 過去の作品を再現・コピーしない
- 今回のテーマに対して独自の解釈で新しい漢字と構造を選ぶ
- interpretationは必ず新しい文章で書く。過去の記録と同じ文を出力してはいけない
- 今回の視点: **${hint}**表現すること`

              // 既存テーマの解釈文を収集（重複チェック用）
              const themeRecords = records.filter(r => r.theme === theme)
              const existingInterps = new Set(
                themeRecords.map(r => r.interpretation).filter(Boolean)
              )

              const userPrompt = `お題「${theme}」に対して、独自の解釈で新しい記号を生成してください。

考察を1〜2行述べてからJSONを出力してください:
{"interpretation":"選択の意図と抽象化の理由を1文で","instances":[{"char":"漢字","removedIndices":[0,1,2],"transform":{"tx":0,"ty":0,"rotate":0,"scale":1,"scaleX":1,"scaleY":1}}]}`

              const MLX_MODEL = '/Users/andotakahiro/ids-symbol-server/ids-symbol-renderer/ids-symbol-renderer/models/qwen3-14b-ids-fused-4bit'
              const apiRes = await fetch('http://localhost:11435/v1/chat/completions', {
                method: 'POST',
                headers: { 'content-type': 'application/json' },
                body: JSON.stringify({
                  model: MLX_MODEL,
                  stream: false,
                  max_tokens: 1800,
                  temperature: 1.1,
                  top_p: 0.95,
                  repetition_penalty: 1.15,
                  messages: [
                    { role: 'system', content: systemPrompt },
                    { role: 'user',   content: userPrompt },
                  ],
                }),
              })
              const apiData = await apiRes.json()
              const rawContent = apiData.choices?.[0]?.message?.content || apiData.message?.content || ''
              // Qwen3 thinking モード: <think>...</think> の後が実際の出力
              const thinkMatch  = rawContent.match(/<think>([\s\S]*?)<\/think>\s*/i)
              const thinkText   = thinkMatch?.[1]?.trim() || ''
              const text        = thinkMatch ? rawContent.slice(thinkMatch[0].length) : rawContent
              console.log('[generate] think:\n', thinkText.slice(0, 300))
              console.log('[generate] response:\n', text)

              // ブラケット対応JSONパーサー（末尾ゴミ対策）
              const extractJSON = src => {
                const start = src.indexOf('{')
                if (start === -1) return null
                let depth = 0, inStr = false, esc = false
                for (let i = start; i < src.length; i++) {
                  const c = src[i]
                  if (esc)          { esc = false; continue }
                  if (c === '\\' && inStr) { esc = true; continue }
                  if (c === '"')    { inStr = !inStr; continue }
                  if (inStr)        continue
                  if (c === '{')    depth++
                  if (c === '}' && --depth === 0) return src.slice(start, i + 1)
                }
                return null
              }
              // <思考>ブロックから解説・概念・選択理由を抽出（Format E が出力された場合）
              // 優先順: <解説>（批評的読解）> <概念> > <選択>
              const extractCot = src => {
                const cotMatch = src.match(/<思考>([\s\S]*?)<\/思考>/)
                if (!cotMatch) return null
                const inner     = cotMatch[1]
                // <解説> は複数行にまたがる可能性があるため次のタグまでを取得
                const kaisetsu  = inner.match(/<解説>([\s\S]*?)(?=<概念>|<選択>|<構造>|$)/)?.[1]?.trim()
                const concept   = inner.match(/<概念>\s*(.+)/)?.[1]?.trim()
                const selection = inner.match(/<選択>\s*(.+)/)?.[1]?.trim()
                return kaisetsu || concept || selection || null
              }

              // JSON前のフリーテキストから reasoning を抽出（Format A が出力された場合）
              const extractPreJsonReasoning = src => {
                const jsonStart = src.indexOf('{')
                if (jsonStart <= 0) return null
                // JSON前のテキストを取得
                const pre = src.slice(0, jsonStart).trim()
                // ASCII以外の文字が多い行（ゴミ文字）を除外し、意味のある日本語行のみ残す
                const lines = pre.split('\n')
                  .map(l => l.trim())
                  .filter(l => {
                    if (l.length < 5) return false
                    // 日本語・漢字・句読点の割合が30%以上の行のみ
                    const jpChars = (l.match(/[\u3000-\u9FFF\uFF00-\uFFEF、。]/g) || []).length
                    return jpChars / l.length >= 0.3
                  })
                if (lines.length === 0) return null
                // 最後の意味ある行（最も具体的な考察が多い）
                return lines[lines.length - 1]
              }

              const cotInterpretation = extractCot(text)
              const preJsonReasoning  = extractPreJsonReasoning(text)

              // コードブロック内を優先
              const codeBlock = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/)?.[1]
              const jsonStr = extractJSON(codeBlock ?? '') || extractJSON(text)
              if (!jsonStr) throw new Error('JSON抽出失敗 (応答: ' + text.slice(0, 300) + ')')
              const result = JSON.parse(jsonStr)

              // interpretationが空・デフォルトなら CoT → JSON前テキスト の順で補完
              const isGeneric = !result.interpretation ||
                result.interpretation.includes('を漢字の組み合わせで表現した') ||
                result.interpretation.length < 8
              if (isGeneric) {
                result.interpretation = cotInterpretation || preJsonReasoning || result.interpretation
              }

              // charからcodeを補完（モデルがcodeを省略してもOK）
              for (const inst of result.instances ?? []) {
                if (!inst.code && inst.char) {
                  inst.code = charToCode.get(inst.char) ?? null
                }
              }
              result.instances = (result.instances ?? []).filter(i => i.code)

              // ── 配置検証 → フィードバック再生成 ──────────────────────────
              const validateLayout = (instances) => {
                const issues = []
                for (const inst of instances) {
                  const t = inst.transform || {}
                  if (Math.abs(t.tx ?? 0) > 52) issues.push(`「${inst.char}」tx=${t.tx}（±52以内にしてください）`)
                  if (Math.abs(t.ty ?? 0) > 52) issues.push(`「${inst.char}」ty=${t.ty}（±52以内にしてください）`)
                  if ((t.scale  ?? 1) > 2.0)    issues.push(`「${inst.char}」scale=${t.scale}（1.8以内にしてください）`)
                  if ((t.scaleX ?? 1) > 2.0)    issues.push(`「${inst.char}」scaleX=${t.scaleX}（1.8以内にしてください）`)
                  if ((t.scaleY ?? 1) > 2.0)    issues.push(`「${inst.char}」scaleY=${t.scaleY}（1.8以内にしてください）`)
                }
                return issues
              }

              const layoutIssues = validateLayout(result.instances)
              if (layoutIssues.length > 0) {
                console.log('[generate] layout issues, requesting correction:\n', layoutIssues.join('\n'))
                const feedbackPrompt = `配置に問題があります:\n${layoutIssues.join('\n')}\n\n上記を修正し、instancesの配置のみ変えたJSONを出力してください（interpretationはそのまま）:\n{"interpretation":"...","instances":[...]}`
                const corrRes = await fetch('http://localhost:11435/v1/chat/completions', {
                  method: 'POST',
                  headers: { 'content-type': 'application/json' },
                  body: JSON.stringify({
                    model: MLX_MODEL,
                    stream: false,
                    max_tokens: 800,
                    temperature: 0.3,
                    messages: [
                      { role: 'system',    content: systemPrompt },
                      { role: 'user',      content: userPrompt },
                      { role: 'assistant', content: text },
                      { role: 'user',      content: feedbackPrompt },
                    ],
                  }),
                })
                const corrData = await corrRes.json()
                const corrRaw  = corrData.choices?.[0]?.message?.content || ''
                const corrThinkMatch = corrRaw.match(/<think>([\s\S]*?)<\/think>\s*/i)
                const corrText = corrThinkMatch ? corrRaw.slice(corrThinkMatch[0].length) : corrRaw
                console.log('[generate] correction response:\n', corrText)
                const corrJsonStr = extractJSON(corrText)
                if (corrJsonStr) {
                  const corrResult = JSON.parse(corrJsonStr)
                  for (const inst of corrResult.instances ?? []) {
                    if (!inst.code && inst.char) inst.code = charToCode.get(inst.char) ?? null
                  }
                  const corrInsts = (corrResult.instances ?? []).filter(i => i.code)
                  if (corrInsts.length > 0) {
                    result.instances = corrInsts
                    if (corrResult.interpretation) result.interpretation = corrResult.interpretation
                  }
                }
              }

              // 既存記録と同じ解釈文なら空にする（暗記再現を防ぐ）
              if (result.interpretation && existingInterps.has(result.interpretation.trim())) {
                console.log('[generate] interpretation matches existing record, clearing')
                result.interpretation = ''
              }

              // 解釈文が長すぎる場合は最初の1文に切り詰める（ループ・テーマ汚染対策）
              if (result.interpretation && result.interpretation.length > 120) {
                console.log('[generate] interpretation too long (' + result.interpretation.length + ' chars), trimming')
                const firstSentence = result.interpretation.match(/^[^。！？]+[。！？]/)?.[0]
                result.interpretation = firstSentence || result.interpretation.slice(0, 80)
              }

              res.setHeader('Content-Type', 'application/json')
              res.end(JSON.stringify(result))
            } catch (e) {
              res.statusCode = 500
              res.end(JSON.stringify({ error: e.message }))
            }
          })
        })

        server.middlewares.use('/api/score', (req, res) => {
          if (req.method !== 'POST') { res.statusCode = 405; res.end(); return }
          let body = ''
          req.on('data', chunk => { body += chunk })
          req.on('end', () => {
            try {
              const { symbol_id, timestamp, graphic, abstraction, remove } = JSON.parse(body)
              const key = symbol_id || timestamp
              if (!key) { res.statusCode = 400; res.end(JSON.stringify({ error: 'no key' })); return }
              // スコアだけを小さな scores.json に保存（results.jsonl は触らない）
              const scoresPath = path.resolve('scores.json')
              const scores = fs.existsSync(scoresPath)
                ? JSON.parse(fs.readFileSync(scoresPath, 'utf8'))
                : {}
              if (remove) { delete scores[key] }
              else { scores[key] = { graphic, abstraction } }
              fs.writeFileSync(scoresPath, JSON.stringify(scores), 'utf8')
              res.setHeader('Content-Type', 'application/json')
              res.end(JSON.stringify({ ok: true }))
            } catch (e) {
              res.statusCode = 500
              res.end(JSON.stringify({ error: e.message }))
            }
          })
        })

        server.middlewares.use('/api/mlx-status', (req, res) => {
          checkMlxReady(running => {
            res.setHeader('Content-Type', 'application/json')
            res.end(JSON.stringify({ running }))
          })
        })

        server.middlewares.use('/api/mlx-start', (req, res) => {
          if (req.method !== 'POST') { res.statusCode = 405; res.end(); return }
          checkMlxReady(running => {
            if (running) {
              res.setHeader('Content-Type', 'application/json')
              res.end(JSON.stringify({ ok: true, status: 'already_running' }))
              return
            }
            if (mlxProc) {
              res.setHeader('Content-Type', 'application/json')
              res.end(JSON.stringify({ ok: true, status: 'starting' }))
              return
            }
            const scriptPath = path.resolve('scripts/start_mlx_server.sh')
            mlxProc = spawn('bash', [scriptPath], { detached: false })
            mlxProc.on('exit', () => { mlxProc = null })
            res.setHeader('Content-Type', 'application/json')
            res.end(JSON.stringify({ ok: true, status: 'starting' }))
          })
        })

        server.middlewares.use('/api/mlx-stop', (req, res) => {
          if (req.method !== 'POST') { res.statusCode = 405; res.end(); return }
          if (mlxProc) { mlxProc.kill('SIGTERM'); mlxProc = null }
          // 既存プロセスも念のため終了
          spawn('pkill', ['-f', 'mlx_lm'], { detached: true })
          res.setHeader('Content-Type', 'application/json')
          res.end(JSON.stringify({ ok: true }))
        })

        server.middlewares.use('/api/trash-list', (req, res) => {
          try {
            const trashPath = path.resolve('trash.jsonl')
            if (!fs.existsSync(trashPath)) { res.setHeader('Content-Type','application/json'); res.end(JSON.stringify([])); return }
            const records = fs.readFileSync(trashPath, 'utf8').split('\n').filter(Boolean)
              .map(l => { try { return JSON.parse(l) } catch { return null } }).filter(Boolean)
            res.setHeader('Content-Type', 'application/json')
            res.end(JSON.stringify(records))
          } catch (e) {
            res.statusCode = 500
            res.end(JSON.stringify({ error: e.message }))
          }
        })

        server.middlewares.use('/api/trash', (req, res) => {
          if (req.method !== 'POST') { res.statusCode = 405; res.end(); return }
          let body = ''
          req.on('data', chunk => { body += chunk })
          req.on('end', () => {
            try {
              const { symbol_id, timestamp } = JSON.parse(body)
              const fileMap = {
                'results.jsonl':        path.resolve('results.jsonl'),
                'ai_results.jsonl':     path.resolve('ai_results.jsonl'),
                'hybrid_results.jsonl': path.resolve('hybrid_results.jsonl'),
              }
              let found = false
              for (const [filename, filePath] of Object.entries(fileMap)) {
                if (!fs.existsSync(filePath)) continue
                const lines = fs.readFileSync(filePath, 'utf8').split('\n').filter(Boolean)
                const idx = lines.findIndex(l => {
                  try {
                    const r = JSON.parse(l)
                    if (symbol_id && r.symbol_id) return r.symbol_id === symbol_id
                    if (timestamp && r.timestamp) return r.timestamp === timestamp
                    return false
                  } catch { return false }
                })
                if (idx === -1) continue
                const record = JSON.parse(lines[idx])
                record._trash_source = filename
                record._trashed_at   = new Date().toISOString()
                lines.splice(idx, 1)
                fs.writeFileSync(filePath, lines.length ? lines.join('\n') + '\n' : '', 'utf8')
                fs.appendFileSync(path.resolve('trash.jsonl'), JSON.stringify(record) + '\n', 'utf8')
                found = true
                break
              }
              res.setHeader('Content-Type', 'application/json')
              res.end(JSON.stringify({ ok: found }))
            } catch (e) {
              res.statusCode = 500
              res.end(JSON.stringify({ error: e.message }))
            }
          })
        })

        server.middlewares.use('/api/restore', (req, res) => {
          if (req.method !== 'POST') { res.statusCode = 405; res.end(); return }
          let body = ''
          req.on('data', chunk => { body += chunk })
          req.on('end', () => {
            try {
              const { symbol_id, timestamp } = JSON.parse(body)
              const trashPath = path.resolve('trash.jsonl')
              if (!fs.existsSync(trashPath)) { res.end(JSON.stringify({ ok: false })); return }
              const lines = fs.readFileSync(trashPath, 'utf8').split('\n').filter(Boolean)
              const idx = lines.findIndex(l => {
                try {
                  const r = JSON.parse(l)
                  if (symbol_id && r.symbol_id) return r.symbol_id === symbol_id
                  if (timestamp && r.timestamp) return r.timestamp === timestamp
                  return false
                } catch { return false }
              })
              if (idx === -1) { res.end(JSON.stringify({ ok: false })); return }
              const record = JSON.parse(lines[idx])
              const sourceFile = record._trash_source || 'results.jsonl'
              delete record._trash_source
              delete record._trashed_at
              lines.splice(idx, 1)
              fs.writeFileSync(trashPath, lines.length ? lines.join('\n') + '\n' : '', 'utf8')
              fs.appendFileSync(path.resolve(sourceFile), JSON.stringify(record) + '\n', 'utf8')
              res.setHeader('Content-Type', 'application/json')
              res.end(JSON.stringify({ ok: true }))
            } catch (e) {
              res.statusCode = 500
              res.end(JSON.stringify({ error: e.message }))
            }
          })
        })

        server.middlewares.use('/api/update-interpretation', (req, res) => {
          if (req.method !== 'POST') { res.statusCode = 405; res.end(); return }
          let body = ''
          req.on('data', chunk => { body += chunk })
          req.on('end', () => {
            try {
              const { symbol_id, timestamp, interpretation } = JSON.parse(body)
              const files = [
                path.resolve('results.jsonl'),
                path.resolve('ai_results.jsonl'),
                path.resolve('hybrid_results.jsonl'),
              ]
              let found = false
              for (const filePath of files) {
                if (!fs.existsSync(filePath)) continue
                const lines = fs.readFileSync(filePath, 'utf8').split('\n').filter(Boolean)
                const idx = lines.findIndex(l => {
                  try {
                    const r = JSON.parse(l)
                    if (symbol_id && r.symbol_id) return r.symbol_id === symbol_id
                    if (timestamp && r.timestamp) return r.timestamp === timestamp
                    return false
                  } catch { return false }
                })
                if (idx === -1) continue
                const record = JSON.parse(lines[idx])
                if (interpretation) record.interpretation = interpretation
                else delete record.interpretation
                lines[idx] = JSON.stringify(record)
                fs.writeFileSync(filePath, lines.join('\n') + '\n', 'utf8')
                found = true
                break
              }
              res.setHeader('Content-Type', 'application/json')
              res.end(JSON.stringify({ ok: found }))
            } catch (e) {
              res.statusCode = 500
              res.end(JSON.stringify({ error: e.message }))
            }
          })
        })

        server.middlewares.use('/api/ai-save', (req, res) => {
          if (req.method !== 'POST') { res.statusCode = 405; res.end(); return }
          let body = ''
          req.on('data', chunk => { body += chunk })
          req.on('end', () => {
            try {
              fs.appendFileSync(path.resolve('ai_results.jsonl'), body + '\n', 'utf8')
              res.setHeader('Content-Type', 'application/json')
              res.end(JSON.stringify({ ok: true }))
            } catch (e) {
              res.statusCode = 500
              res.end(JSON.stringify({ error: e.message }))
            }
          })
        })

        server.middlewares.use('/api/hybrid-save', (req, res) => {
          if (req.method !== 'POST') { res.statusCode = 405; res.end(); return }
          let body = ''
          req.on('data', chunk => { body += chunk })
          req.on('end', () => {
            try {
              fs.appendFileSync(path.resolve('hybrid_results.jsonl'), body + '\n', 'utf8')
              res.setHeader('Content-Type', 'application/json')
              res.end(JSON.stringify({ ok: true }))
            } catch (e) {
              res.statusCode = 500
              res.end(JSON.stringify({ error: e.message }))
            }
          })
        })

        // ── research endpoints ──────────────────────────────────────────
        server.middlewares.use('/api/research', (req, res) => {
          res.setHeader('Content-Type', 'application/json')

          if (req.method === 'GET') {
            // return cached patterns.json
            try {
              const p = path.resolve('research/patterns.json')
              if (fs.existsSync(p)) {
                res.end(fs.readFileSync(p, 'utf8'))
              } else {
                res.end(JSON.stringify({ patterns: [], generated_at: null }))
              }
            } catch (e) {
              res.statusCode = 500
              res.end(JSON.stringify({ error: e.message }))
            }
            return
          }

          if (req.method === 'POST') {
            // run auto_research.py in background
            const scriptPath = path.resolve('scripts/auto_research.py')
            const child = spawn('python3', [scriptPath], {
              cwd: path.resolve('.'),
              stdio: ['ignore', 'pipe', 'pipe'],
            })
            let out = ''
            let err = ''
            child.stdout.on('data', d => { out += d })
            child.stderr.on('data', d => { err += d })
            child.on('close', code => {
              console.log('[research] exit', code, out.slice(-200))
              if (err) console.error('[research stderr]', err.slice(-200))
            })
            res.end(JSON.stringify({ ok: true, message: '研究を開始しました' }))
            return
          }

          res.statusCode = 405
          res.end(JSON.stringify({ error: 'method not allowed' }))
        })

        server.middlewares.use('/api/save', (req, res) => {
          if (req.method !== 'POST') {
            res.statusCode = 405
            res.end()
            return
          }
          let body = ''
          req.on('data', chunk => { body += chunk })
          req.on('end', () => {
            try {
              const filePath = path.resolve('results.jsonl')
              fs.appendFileSync(filePath, body + '\n', 'utf8')
              res.setHeader('Content-Type', 'application/json')
              res.end(JSON.stringify({ ok: true }))
            } catch (e) {
              res.statusCode = 500
              res.end(JSON.stringify({ error: e.message }))
            }
          })
        })
      }
    }
  ]
})
