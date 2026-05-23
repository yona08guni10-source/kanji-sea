FROM python:3.11-slim

WORKDIR /app
COPY scripts/app.py scripts/app.py
COPY scripts/site.py scripts/site.py

ENV PORT=7860
EXPOSE $PORT

CMD ["python", "scripts/app.py"]
