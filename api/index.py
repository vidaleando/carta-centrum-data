"""Vercel serverless entry point: the FastAPI app from backend/app.

vercel.json rewrites /api/*, /health and the API docs here; the frontend
is served by Vercel as static files.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402,F401
