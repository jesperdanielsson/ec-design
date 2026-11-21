"""Arkitekturregel: kärnan får aldrig importera API, GUI eller app."""

import ast
from pathlib import Path

CORE = Path(__file__).resolve().parents[1] / "src" / "ecdesign" / "core"
FORBIDDEN = ("ecdesign.api", "ecdesign.app", "ecdesign.report", "ecdesign.export", "webview")


def test_core_is_independent():
    for path in CORE.rglob("*.py"):
        tree = ast.parse(path.read_text("utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert node.level <= 2 or not mod.startswith(("api", "app")), path
                assert not mod.startswith(FORBIDDEN), f"{path} importerar {mod}"
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(FORBIDDEN), f"{path} importerar {alias.name}"
