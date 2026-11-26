"""The API's error messages in English: every message the backend raises has a translation."""
import ast
import json
from pathlib import Path

import pytest

from api_gateway import dispatch
from memory_repository import MemoryRepository
from pulse_core.ports import Dependencies
from pulse_core.i18n import LABELS, language, translate

BACKEND = Path(__file__).resolve().parents[2] / "backend"
ERRORS = {"ValidationError", "NotFound", "Conflict", "BusinessError"}


def raised_messages():
    """Every literal message in `raise ValidationError("...")` (and NotFound, Conflict) of the backend,
    plus every label passed to the field helpers (text, cents, day, moment, minutes)."""
    messages, labels = set(), set()
    for path in BACKEND.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", getattr(node.func, "attr", ""))
            if name in ERRORS and node.args and isinstance(node.args[0], ast.Constant):
                messages.add(node.args[0].value)
            if name in ("text", "cents", "day", "moment", "minutes"):
                for arg in node.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value[:1].isupper():
                        labels.add(arg.value)
    return messages, labels


def test_every_message_and_label_has_an_english_translation():
    messages, labels = raised_messages()
    assert len(messages) > 30
    untranslated = [m for m in messages if translate(m, "en") == m]
    assert not untranslated, untranslated
    assert not labels - set(LABELS), labels - set(LABELS)


@pytest.mark.parametrize("message, english", [
    ("Nome: obrigatório", "Name: required"),
    ("Nome: no máximo 100 caracteres", "Name: at most 100 characters"),
    ("Valor hora: deve ser maior que zero", "Hourly rate: must be greater than zero"),
    ("Período de no máximo 400 dias", "A period of at most 400 days"),
    ("Tarefa já faturada: o tempo não muda mais", "Task already billed: its time can't change any more"),
])
def test_messages_with_a_label_or_a_number(message, english):
    assert translate(message, "en") == english
    assert translate(message, "pt-BR") == message


def test_language_from_the_header():
    assert language("en-US,en;q=0.9") == "en"
    assert language("pt-BR,pt;q=0.9,en;q=0.8") == "pt-BR"
    assert language(None) == "pt-BR"


def test_the_api_answers_in_the_requests_language():
    deps = Dependencies(MemoryRepository())

    def create_company(headers):
        event = {"rawPath": "/companies", "requestContext": {"http": {"method": "POST"},
                 "authorizer": {"jwt": {"claims": {"sub": "u1"}}}}, "headers": headers,
                 "body": json.dumps({"name": ""})}
        response = dispatch(event, deps)
        return response["statusCode"], json.loads(response["body"])

    assert create_company({"accept-language": "en-US,en;q=0.9"}) == (400, {"error": "Name: required"})
    assert create_company({}) == (400, {"error": "Nome: obrigatório"})
