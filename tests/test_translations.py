"""Every text of the interface has an English translation.

Portuguese is the source language: texts are written in Portuguese in the
code and templates, and translated in src/locale/en/LC_MESSAGES/django.po
(compiled to django.mo, which is what Django reads).

These tests find the texts the way ``makemessages`` does: gettext calls
with literal text in the Python code, and {% translate %} and
{% blocktranslate %} in the templates. So a new text without a
translation, or a translation nobody uses anymore, fails here.
"""

import ast
import gettext
from pathlib import Path

from django.template import engines
from django.templatetags.i18n import BlockTranslateNode, TranslateNode
from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "src"
CATALOG = APP / "locale" / "en" / "LC_MESSAGES" / "django.mo"

# name -> (position of the context, position of the text, has a plural)
GETTEXT_CALLS = {
    "_": (None, 0, False),
    "gettext": (None, 0, False),
    "gettext_lazy": (None, 0, False),
    "ngettext": (None, 0, True),
    "ngettext_lazy": (None, 0, True),
    "pgettext": (0, 1, False),
    "pgettext_lazy": (0, 1, False),
    "npgettext": (0, 1, True),
    "npgettext_lazy": (0, 1, True),
}


class Message(tuple):
    """``(context, text, plural)``; context and plural may be None."""

    def __new__(cls, context, text, plural=None):
        return super().__new__(cls, (context, text, plural))

    @property
    def key(self):
        """The key of the text in a compiled catalog."""
        context, text, plural = self
        key = f"{context}\x04{text}" if context else text
        return (key, 0) if plural else key


def _is_text(node):
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def python_messages():
    """Messages of the gettext calls in src/, and calls without literal text."""
    messages, not_literal = set(), []
    for path in sorted(APP.rglob("*.py")):
        if "migrations" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", getattr(node.func, "attr", None))
            if name not in GETTEXT_CALLS:
                continue
            context_at, text_at, has_plural = GETTEXT_CALLS[name]
            positions = [p for p in (context_at, text_at) if p is not None]
            if has_plural:
                positions.append(text_at + 1)
            values = [node.args[p] if p < len(node.args) else None for p in positions]
            if not all(_is_text(value) for value in values):
                not_literal.append(f"{path.relative_to(ROOT)}:{node.lineno}")
                continue
            values = [v.value for v in values]
            context = values.pop(0) if context_at is not None else None
            messages.add(Message(context, *values))
    return messages, not_literal


def template_messages():
    """Messages of {% translate %} and {% blocktranslate %} in the templates."""
    engine = engines["django"]
    messages = set()
    for path in sorted((APP / "templates").rglob("*.html")):
        source = path.read_text(encoding="utf-8")
        nodelist = engine.from_string(source).template.nodelist
        for node in nodelist.get_nodes_by_type(TranslateNode):
            text = node.filter_expression.var.literal
            context = node.message_context and node.message_context.var.literal
            messages.add(Message(context, text))
        for node in nodelist.get_nodes_by_type(BlockTranslateNode):
            singular, _ = node.render_token_list(node.singular)
            plural = node.render_token_list(node.plural)[0] if node.plural else None
            context = node.message_context and node.message_context.var.literal
            messages.add(Message(context, singular, plural))
    return messages


def every_message():
    return python_messages()[0] | template_messages()


def english_catalog():
    with CATALOG.open("rb") as file:
        return gettext.GNUTranslations(file)._catalog


class TranslationTests(SimpleTestCase):
    def test_translation_calls_use_literal_text(self):
        # makemessages only finds literal text: gettext(variable) is never
        # translated.
        self.assertEqual(python_messages()[1], [])

    def test_every_text_has_an_english_translation(self):
        catalog = english_catalog()
        missing = sorted(
            message for message in every_message() if not catalog.get(message.key)
        )
        self.assertEqual(missing, [], "Translate them in src/locale/en (see README).")

    def test_plural_texts_have_both_english_forms(self):
        catalog = english_catalog()
        for message in every_message():
            if message[2]:
                with self.subTest(message=message[1]):
                    key = message.key[0]
                    self.assertTrue(catalog.get((key, 0)) and catalog.get((key, 1)))

    def test_no_unused_translations(self):
        used = {m.key[0] if m[2] else m.key for m in every_message()}
        unused = {
            key[0] if isinstance(key, tuple) else key for key in english_catalog()
        } - used - {""}  # "" is the catalog's header
        self.assertEqual(sorted(unused), [])
