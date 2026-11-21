"""Liten HTTP-brygga för utveckling i webbläsaren.

I skrivbordsappen anropar gränssnittet Python direkt via pywebview. När man
utvecklar gränssnittet i en vanlig webbläsare (``npm run dev``) finns ingen
pywebview, så då går anropen hit i stället: ``POST /api/<metod>`` med
argumenten som en JSON-lista. Vite skickar ``/api`` vidare hit (se vite.config.ts).

Kör: ``python -m ecdesign.devserver`` (port 8765).
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .api import Api

PORT = 8765
_api = Api()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        name = self.path.removeprefix("/api/")
        method = getattr(_api, name, None)
        if name.startswith("_") or not callable(method):
            self._send(404, {"error": f"Okänd metod {name!r}"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        args = json.loads(self.rfile.read(length) or b"[]")
        try:
            self._send(200, method(*args))
        except Exception as exc:  # visa felet i gränssnittet i stället för att krascha
            self._send(400, {"error": str(exc)})

    def _send(self, status: int, payload: object) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    print(f"API-brygga på http://localhost:{PORT}/api")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
