#!/usr/bin/env python3
"""
app.py — Nonsense Kanji ショーケースサイト起動
"""
import os, sys
from pathlib import Path

os.environ["PORT"] = os.environ.get("PORT", "7860")
exec(open(Path(__file__).parent / "site.py").read())
