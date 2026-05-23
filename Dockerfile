FROM python:3.11-slim

# 日本語フォント + 基本パッケージ
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依存ライブラリ（キャッシュ活用のため先にコピー）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーション本体
COPY . .

# PORT は環境変数で上書き可能（HF Spaces: 7860, Render: 動的）
ENV PORT=7860
EXPOSE $PORT

CMD ["python", "scripts/app.py"]
