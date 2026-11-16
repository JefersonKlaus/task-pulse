"""The layers of src/ (the app) only depend downwards.

    domain  <-  models  <-  integrations  <-  services  <-  forms  <-  views

src/taskpulse/ (settings, root URLs, WSGI) is configuration: it imports no
app code, and no app code imports it.

* domain: business rules, no database or HTTP;
* integrations: the exchange-rate API and the CSV format;
* services: use cases (combine the layers below);
* forms and views: HTTP input and output only.

These tests read the imports of every module, so a dependency in the wrong
direction fails here instead of growing unnoticed.
"""

import ast
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "src"

ALLOWED = {
    "domain": set(),
    "models": {"domain"},
    "integrations": {"domain", "models"},
    "services": {"domain", "integrations", "models"},
    "forms": {"domain", "integrations", "models", "services"},
    "views": {"domain", "forms", "integrations", "models", "services"},
    "templatetags": {"domain"},
    "admin": {"domain", "models"},
    "taskpulse": set(),
}


def layer_of(path):
    first = path.relative_to(APP).parts[0]
    return first[: -len(".py")] if first.endswith(".py") else first


def modules():
    for path in sorted(APP.rglob("*.py")):
        if "migrations" not in path.parts:
            yield path


def imported_modules(path):
    """Absolute names of the modules ``path`` imports (relative ones resolved)."""
    package = list(path.relative_to(ROOT).with_suffix("").parts)
    if path.name != "__init__.py":
        package = package[:-1]
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[: len(package) - node.level + 1]
                yield ".".join(base + ([node.module] if node.module else []))
            else:
                yield node.module


def imported_layers(path):
    for name in imported_modules(path):
        parts = name.split(".")
        if parts[0] == "src" and len(parts) > 1:
            yield parts[1]


class LayerDependencyTests(SimpleTestCase):
    def test_layers_only_depend_downwards(self):
        for path in modules():
            layer = layer_of(path)
            if layer not in ALLOWED:
                continue
            wrong = set(imported_layers(path)) - ALLOWED[layer] - {layer}
            with self.subTest(module=str(path.relative_to(ROOT))):
                self.assertEqual(wrong, set(), f"{layer} must not import {wrong}")

    def test_domain_does_no_http_or_database_work(self):
        # urllib.parse (string parsing) is fine; urllib.request is HTTP.
        forbidden = (
            "urllib.request",
            "http.",
            "requests",
            "socket",
            "django.db.transaction",
        )
        for path in (APP / "domain").glob("*.py"):
            imported = set(imported_modules(path))
            with self.subTest(module=path.name):
                self.assertFalse(
                    [name for name in imported if name.startswith(forbidden)]
                )
