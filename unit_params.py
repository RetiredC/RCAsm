# This file is a part of RCAsm software
# (c) 2026, RetiredCoder (RC)
# License: GPLv3, see "LICENSE.TXT" file
# https://github.com/RetiredC

from typing import Dict, Tuple
import utils

def _split_outside_quotes(text: str, sep: str = ",") -> list[str] | None:
    """Split by sep, but ignore separators inside single/double quotes."""
    parts: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    escaped = False

    for ch in text:
        if escaped:
            buf.append(ch)
            escaped = False
            continue

        if ch == "\\":
            # Keep backslash; we'll unescape later if needed
            buf.append(ch)
            escaped = True
            continue

        if quote is not None:
            if ch == quote:
                quote = None
            buf.append(ch)
            continue

        # Not inside quotes
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            continue

        if ch == sep:
            parts.append("".join(buf).strip())
            buf.clear()
            continue

        buf.append(ch)

    if quote is not None or escaped:
        # Unclosed quote or trailing backslash
        return None

    parts.append("".join(buf).strip())
    return parts


def _find_unquoted(text: str, target: str) -> int:
    """Find target char outside quotes; return index or -1."""
    quote: str | None = None
    escaped = False

    for i, ch in enumerate(text):
        if escaped:
            escaped = False
            continue

        if ch == "\\":
            escaped = True
            continue

        if quote is not None:
            if ch == quote:
                quote = None
            continue

        if ch in ("'", '"'):
            quote = ch
            continue

        if ch == target:
            return i

    return -1


def _unescape_quoted(inner: str) -> str:
    """Unescape common backslash escapes inside a quoted string."""
    out: list[str] = []
    i = 0
    n = len(inner)
    while i < n:
        ch = inner[i]
        if ch == "\\" and i + 1 < n:
            nxt = inner[i + 1]
            if nxt == "n":
                out.append("\n")
            elif nxt == "t":
                out.append("\t")
            elif nxt == "r":
                out.append("\r")
            elif nxt in ('\\', '"', "'"):
                out.append(nxt)
            else:
                # Unknown escape: keep the escaped char as-is
                out.append(nxt)
            i += 2
            continue

        out.append(ch)
        i += 1
    return "".join(out)


def parse_unit_params(s: str) -> Tuple[str, Dict[str, int | str]] | None:
    """Parse 'name(key=value, ...)' into (name, {key: value, ...})."""
    s = s.strip()

    # Find parentheses
    l_paren = s.find("(")
    r_paren = s.rfind(")")
    if l_paren == -1 or r_paren == -1 or r_paren < l_paren:
        return None

    # Extract name and parameters substring
    name = s[:l_paren].strip()
    params_str = s[l_paren + 1 : r_paren].strip()

    params: Dict[str, int | str] = {}
    if not params_str:
        return name, params

    parts = _split_outside_quotes(params_str, sep=",")
    if parts is None:
        return None

    for part in parts:
        part = part.strip()
        if not part:
            continue

        eq = _find_unquoted(part, "=")
        if eq == -1:
            return None

        key = part[:eq].strip()
        value = part[eq + 1 :].strip()
        if not key:
            return None
        if (key[-1] >= "0") and (key[-1] <= "9"):
            utils.to_log(f"digits at the end of var are not allowed: {params_str} - {key}")
            return None

        # Quoted string value
        if len(value) >= 2 and value[0] in ("'", '"') and value[-1] == value[0]:
            inner = value[1:-1]
            params[key] = _unescape_quoted(inner)
            continue

        # Try to convert value to int (supports decimal and hex like 0xFF)
        try:
            params[key] = int(value, 0)
        except ValueError:
            params[key] = value

    return name, params

