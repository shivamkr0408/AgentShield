"""Local Flask test website standing in for the Acme intranet (http://acme.test).

Run ``python -m agents.website`` to browse the pristine site at http://127.0.0.1:5050.
"""

from __future__ import annotations

import argparse
import threading
from pathlib import Path

from flask import Flask, Response, abort
from werkzeug.security import safe_join
from werkzeug.serving import BaseWSGIServer, WSGIRequestHandler, make_server

WORLD_SITE = Path(__file__).resolve().parent / "world" / "site"


def create_site(site_dir: Path) -> Flask:
    app = Flask(__name__)

    @app.get("/", defaults={"page": "index"})
    @app.get("/<path:page>")
    def serve(page: str) -> Response:
        relative = page.strip("/") or "index"
        path = safe_join(str(site_dir), f"{relative}.html")
        if path is None or not Path(path).is_file():
            abort(404)
        return Response(Path(path).read_text(encoding="utf-8"), mimetype="text/html")

    return app


class _QuietRequestHandler(WSGIRequestHandler):
    def log_request(self, *args: object, **kwargs: object) -> None:
        pass


class SiteServer:
    """Serves a site directory on an ephemeral localhost port in a background thread."""

    def __init__(self, site_dir: Path, host: str = "127.0.0.1", port: int = 0) -> None:
        self._server: BaseWSGIServer = make_server(
            host, port, create_site(site_dir), threaded=True, request_handler=_QuietRequestHandler
        )
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def base_url(self) -> str:
        return f"http://{self._server.host}:{self._server.server_port}"

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the Acme test intranet.")
    parser.add_argument("--port", type=int, default=5050)
    args = parser.parse_args()
    create_site(WORLD_SITE).run(host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
