"""Normalize extracted knowledge text before chunking."""

from __future__ import annotations

import re

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n{3,}")


def clean_text(raw: str) -> str:
    if not raw:
        return ""
    text = _CONTROL_CHARS.sub("", raw)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in text.split("\n"):
        lines.append(_WHITESPACE.sub(" ", line).strip())
    text = "\n".join(lines)
    text = _BLANK_LINES.sub("\n\n", text)
    return text.strip()