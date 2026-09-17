"""Vercel serverless entrypoint — re-exports the Flask app.

Vercel's Python runtime turns every file under api/ into a function and
looks for an `app` variable. vercel.json rewrites all routes here, and
Flask serves the pages, APIs and static files itself.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app as flask_app  # noqa: E402


class _VercelPathFix:
    """WSGI middleware: Vercel invokes this file at its own path, and the
    rewritten destination (/api/index.py) can leak into PATH_INFO. Flask
    then matches no route and returns its "Not Found" page. Stripping the
    prefix fixes routing on Vercel while leaving local `python app.py`
    behaviour untouched.
    """

    PREFIXES = ("/api/index.py", "/api/index")

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO") or "/"
        for prefix in self.PREFIXES:
            if path == prefix:
                environ["PATH_INFO"] = "/"
                break
            if path.startswith(prefix + "/"):
                environ["PATH_INFO"] = path[len(prefix):]
                break
        return self.wsgi_app(environ, start_response)


flask_app.wsgi_app = _VercelPathFix(flask_app.wsgi_app)

app = flask_app  # Vercel looks for `app`
