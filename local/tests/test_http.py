"""The API as API Gateway calls it: routes from lambda.json, login, ids, bodies and status codes."""
import json
from pathlib import Path

import pytest

from api_gateway import ROUTES, dispatch
from memory_repository import MemoryRepository
from pulse_core.ports import Dependencies

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def call():
    deps = Dependencies(MemoryRepository())

    def call(method, path, body=None, query=None, user="u1", raw=None):
        event = {"rawPath": path, "requestContext": {"http": {"method": method}},
                 "queryStringParameters": query, "body": raw if raw is not None else json.dumps(body) if body else ""}
        if user:
            event["requestContext"]["authorizer"] = {"jwt": {"claims": {"sub": user}}}
        response = dispatch(event, deps)
        return response["statusCode"], json.loads(response["body"]) if response["body"] else None
    return call


def test_every_lambda_has_a_route_and_a_database_access():
    for config in (ROOT / "backend" / "lambdas").glob("*/lambda.json"):
        data = json.loads(config.read_text(encoding="utf-8"))
        assert data["database"] in ("read", "write"), config
        method = data["route"].split()[0]
        assert (data["database"] == "read") == (method == "GET"), config
    assert len(ROUTES) == len(list((ROOT / "backend" / "lambdas").glob("*/lambda.json")))


def test_full_flow_status_codes(call):
    status, company = call("POST", "/companies", {"name": "Etho"})
    assert status == 201
    status, project = call("POST", "/projects", {"company_id": company["id"], "name": "Portal",
                                                 "rule": {"kind": "fixed", "starts_at": "2026-01-01",
                                                          "fixed_cents": 1000}})
    assert status == 201 and project["company_name"] == "Etho"
    status, task = call("POST", f"/projects/{project['id']}/tasks",
                        {"name": "Login", "status": "DONE", "minutes": 30, "started_at": "2026-11-02T10:00",
                         "finished_at": "2026-11-02T12:00"})
    assert status == 201 and task["value_cents"] == 1000
    status, report = call("GET", f"/projects/{project['id']}/billing", query={"from": "2026-11-01", "to": "2026-11-30"})
    assert status == 200 and report["totals"]["to_receive_cents"] == 1000
    assert call("DELETE", f"/projects/{project['id']}/tasks/{task['id']}") == (204, None)
    assert call("DELETE", f"/companies/{company['id']}")[0] == 409


def test_without_login_is_401_and_bad_ids_are_404(call):
    assert call("GET", "/companies", user=None)[0] == 401
    assert call("GET", "/projects/..%2F")[0] == 404
    assert call("GET", "/nothing")[0] == 404
    assert call("PATCH", "/companies")[0] == 404


def test_bad_bodies_are_400(call):
    assert call("POST", "/companies", raw="not json")[0] == 400
    assert call("POST", "/companies", raw="[1]")[0] == 400
    assert call("POST", "/companies", raw="x" * 30_000)[0] == 400
    status, body = call("POST", "/companies", {"name": ""})
    assert status == 400 and body["error"] == "Name: required"         # English unless asked for pt-BR
