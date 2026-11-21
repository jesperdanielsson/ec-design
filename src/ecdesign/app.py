"""Startar skrivbordsappen: ett pywebview-fönster med React-gränssnittet.

Kör ``ecdesign`` (eller ``python -m ecdesign.app``).

- Om ``ui/dist`` finns (efter ``npm run build``) laddas den byggda appen.
- Annars, eller med ``--dev``, laddas Vite-servern på http://localhost:5173
  (starta den med ``npm run dev`` i ``ui/``).
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .api import Api

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "ui" / "dist" / "index.html"
DEV_URL = os.environ.get("ECDESIGN_DEV_URL", "http://localhost:5173")


def main() -> None:
    parser = argparse.ArgumentParser(description="Eurokod-dimensionering")
    parser.add_argument(
        "--dev", action="store_true", help="ladda Vite-servern i stället för ui/dist"
    )
    parser.add_argument("--debug", action="store_true", help="öppna utvecklarverktyg")
    args = parser.parse_args()

    try:
        import webview
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("pywebview saknas. Installera med: pip install -e '.[app]'") from exc

    url = DEV_URL if args.dev or not DIST.exists() else str(DIST)
    webview.create_window(
        "EC Design – betongbalk", url, js_api=Api(), width=1400, height=900, min_size=(1000, 700)
    )
    webview.start(debug=args.debug)


if __name__ == "__main__":
    main()
