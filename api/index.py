"""Vercel serverless entrypoint — re-exports the Flask app.

Vercel's Python runtime turns every file under api/ into a function and
looks for an `app` variable. vercel.json rewrites all routes here, and
Flask serves the pages, APIs and static files itself.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app  # noqa: E402,F401  (Vercel expects `app`)
