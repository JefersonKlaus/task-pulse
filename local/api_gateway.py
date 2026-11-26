"""Plays API Gateway locally: finds which Lambda answers a request and calls it.

The routes come from backend/lambdas/<action>/lambda.json, the same files Terraform reads to create
the real routes, so the local server and the tests see exactly the API that is deployed. Like the
real API Gateway, a path or method with no route is 404 and the Lambda is never called."""
from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
LAMBDAS = ROOT / "backend" / "lambdas"
for folder in (ROOT / "backend" / "core", LAMBDAS):     # what each Lambda's zip has at its root
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from pulse_core.adapters.api_gateway import response  # noqa: E402
from pulse_core.ports import Dependencies              # noqa: E402


def _load_routes() -> list[tuple[str, re.Pattern, str, Callable]]:
    routes = []
    for config in sorted(LAMBDAS.glob("*/lambda.json")):
        name = config.parent.name
        method, path = json.loads(config.read_text(encoding="utf-8"))["route"].split(" ", 1)
        pattern = re.compile("^" + re.sub(r"\\\{(\w+)\\\}", r"(?P<\1>[^/]+)", re.escape(path)) + "$")
        routes.append((method, pattern, name, importlib.import_module(f"{name}.handler").handle))
    return routes


ROUTES = _load_routes()


def dispatch(event: dict[str, Any], deps: Dependencies) -> dict[str, Any]:
    """`event` as API Gateway builds it (rawPath, method, query, body, claims); fills pathParameters."""
    method, path = event["requestContext"]["http"]["method"], event.get("rawPath", "")
    for route_method, pattern, _, handle in ROUTES:
        match = pattern.match(path)
        if match and route_method == method:
            return handle({**event, "pathParameters": match.groupdict() or None}, deps)
    return response(404, {"message": "Not Found"})     # what API Gateway answers, without calling a Lambda
