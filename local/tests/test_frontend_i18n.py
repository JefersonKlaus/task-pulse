"""The site in English: every text the frontend shows (t("...") or N_("...")) has its English in
frontend/src/i18n.ts, with the same {values}, and no English is left without a use."""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
STRING = r'"((?:[^"\\]|\\.)*)"'
CALL = re.compile(r"\b(?:t|N_)\(\s*(" + STRING + r"(?:\s*\+\s*" + STRING + r")*)")
ENTRY = re.compile(r"^\s*" + STRING + r":\s*" + STRING + r",\s*$", re.M)


def unquote(text):
    return text.replace('\\"', '"').replace("\\\\", "\\")


def texts():
    found = set()
    for path in SRC.rglob("*.ts"):
        for match in CALL.finditer(path.read_text(encoding="utf-8")):
            found.add(unquote("".join(re.findall(STRING, match.group(1)))))
    return found


def english():
    source = (SRC / "i18n.ts").read_text(encoding="utf-8")
    block = source[source.index("const EN: Record<string, string> = {"):]
    return {unquote(pt): unquote(en) for pt, en in ENTRY.findall(block)}


def test_every_text_has_its_english():
    used, translated = texts(), english()
    assert len(used) > 150
    missing = sorted(used - set(translated))
    assert not missing, missing


def test_values_match_and_nothing_is_left_over():
    used, translated = texts(), english()
    for pt, en in translated.items():
        assert set(re.findall(r"\{\w+\}", pt)) == set(re.findall(r"\{\w+\}", en)), pt
    assert not set(translated) - used, sorted(set(translated) - used)


if __name__ == "__main__":                      # prints the texts still without English
    for text in sorted(texts() - set(english())):
        print(text)
