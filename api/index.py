"""Vercel serverless entrypoint — re-exports the Flask app.

Vercel's Python runtime turns every file under api/ into a function and
looks for an `app` variable. vercel.json rewrites all routes here, and
Flask serves the pages, APIs and static files itself.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app as flask_app  # noqa: E402


@flask_app.get("/__vercel_debug")
def __vercel_debug():
    """Temporary diagnostic: shows exactly what path Vercel hands Flask."""
    from flask import request

    env = request.environ
    return {
        "path": request.path,
        "script_root": request.script_root,
        "PATH_INFO": env.get("PATH_INFO"),
        "REQUEST_URI": env.get("REQUEST_URI"),
        "SCRIPT_NAME": env.get("SCRIPT_NAME"),
        "HTTP_X_VERCEL_REWRITE": env.get("HTTP_X_VERCEL_REWRITE"),
    }


class _VercelPathFix:
    """WSGI middleware for Vercel routing quirks.

    1. Vercel invokes this file at its own path, and the rewritten
       destination (/api/index.py) can leak into PATH_INFO. Flask then
       matches no route and returns its "Not Found" page.
    2. Single-page-app fallback: any path that is not the homepage, an
       API route, a static asset, or the debug route serves the homepage
       instead of a bare 404.
    Local `python app.py` behaviour is untouched (paths there are clean).
    """

    PREFIXES = ("/api/index.py", "/api/index")
    PASSTHROUGH = ("/api/", "/static/", "/__vercel_debug")

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO") or "/"
        print(f"[phishnet] incoming PATH_INFO={path!r}", flush=True)
        for prefix in self.PREFIXES:
            if path == prefix:
                path = "/"
                break
            if path.startswith(prefix + "/"):
                path = path[len(prefix):]
                break
        if path != "/" and not path.startswith(self.PASSTHROUGH):
            path = "/"
        environ["PATH_INFO"] = path
        return self.wsgi_app(environ, start_response)


flask_app.wsgi_app = _VercelPathFix(flask_app.wsgi_app)

app = flask_app  # Vercel looks for `app`
