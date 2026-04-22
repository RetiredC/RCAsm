# This file is a part of RCAsm software
# (c) 2026, RetiredCoder (RC)
# License: GPLv3, see "LICENSE.TXT" file
# https://github.com/RetiredC

import json
import os
import shutil
from pathlib import Path
from typing import Optional, TYPE_CHECKING, List, Tuple, Dict, Set
from dataclasses import dataclass
from PyQt5.QtCore import QByteArray
from PyQt5.QtWidgets import QFileDialog, QWidget
import defs, exp, re

########################################################################################################################

def load_ide_options():
    config_path = Path(__file__).with_name("config.json")
    if not config_path.exists():
        return
    try:
        text = config_path.read_text(encoding="utf-8")
        data = json.loads(text)
    except Exception:
        return
    if isinstance(data.get("SM_VER"), int):
        defs.SM_VER = data["SM_VER"]
    if isinstance(data.get("AUTO_RUN"), bool):
        defs.AUTO_RUN = data["AUTO_RUN"]
    geom_hex = data.get("WND_GEOMETRY")
    if isinstance(geom_hex, str) and geom_hex:
        try:
            ba = QByteArray.fromHex(geom_hex.encode("ascii"))
            defs.WND_GEOMETRY = ba
        except Exception:
            defs.WND_GEOMETRY = QByteArray()
    else:
        defs.WND_GEOMETRY = QByteArray()
    spl_hex = data.get("SPL_STATE")
    if isinstance(spl_hex, str) and spl_hex:
        try:
            ba = QByteArray.fromHex(spl_hex.encode("ascii"))
            defs.SPL_STATE = ba
        except Exception:
            defs.SPL_STATE = QByteArray()
    else:
        defs.SPL_STATE = QByteArray()
    if isinstance(data.get("PROJECT_PATH"), str):
        defs.PROJECT_PATH = data["PROJECT_PATH"]

def save_ide_options():
    config_path = Path(__file__).with_name("config.json")
    if isinstance(defs.WND_GEOMETRY, QByteArray) and not defs.WND_GEOMETRY.isEmpty():
        geom_hex = bytes(defs.WND_GEOMETRY.toHex()).decode("ascii")
    else:
        geom_hex = ""
    if isinstance(defs.SPL_STATE, QByteArray) and not defs.SPL_STATE.isEmpty():
        spl_hex = bytes(defs.SPL_STATE.toHex()).decode("ascii")
    else:
        spl_hex = ""
    data = {
        "SM_VER": defs.SM_VER,
        "AUTO_RUN": defs.AUTO_RUN,
         "WND_GEOMETRY": geom_hex,
        "SPL_STATE":spl_hex,
        "PROJECT_PATH":defs.PROJECT_PATH
    }
    text = json.dumps(data, ensure_ascii=False, indent=2)
    config_path.write_text(text, encoding="utf-8")

if TYPE_CHECKING:
    # This import is only for type checkers, not at runtime
    from editor import MainWindow
_main_window: Optional["MainWindow"] = None
def set_main_window(win):
    global _main_window
    _main_window = win
def to_log(s: str, clear: bool = False):
    if _main_window is None:
        print(s)
        return
    editor = _main_window.log_editor
    if clear:
        editor.clear()
    editor.append_line(s)
def clear_log():
    if not (_main_window is None):
        _main_window.log_editor.clear()

def select_folder(parent: QWidget | None = None,
                  title: str = "Select folder",
                  initial_dir: str = "") -> str:
    # Returns selected directory path, or "" if canceled.
    options = QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
    path = QFileDialog.getExistingDirectory(parent, title, initial_dir, options)
    return path or ""

def get_project_files(p: Path | str) -> list[str]:
    base_dir = Path(p)
    if not base_dir.is_dir():
        return []
    asm_files = [e for e in base_dir.iterdir() if e.is_file() and e.suffix.lower() == ".asm"]
    def sort_key(f: Path):
        name = f.name.lower()
        return (0 if name == "main.asm" else 1, name)
    asm_files.sort(key=sort_key)
    return [str(f) for f in asm_files]

def load_str_from_file(p: Path | str) -> str:
    path = Path(p)
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")

def save_str_to_file(s: str, p: Path | str) -> None:
    path = Path(p)
    path.write_text(s, encoding="utf-8")

def load_list_from_file(p: Path | str) -> List[str]:
    path = Path(p)
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    return text.splitlines()

def save_list_to_file(lines: List[str], p: Path | str) -> None:
    path = Path(p)
    text = "\n".join(lines)
    path.write_text(text, encoding="utf-8")

def is_char_letter(s: str) -> bool:
    return (s[0] >= "A" and s[0] <= "Z") or (s[0] >= "a" and s[0] <= "z") or (s[0] == "_")

# add_offset("Ri", "R", 5, "IADD3 Ri, R15, Ri5, 0x00") returns "IADD3 R5, R15, R10, 0x00"
def add_offset(old_name: str, new_name: str, ofs: int, line: str) -> str:
    # Replace occurrences of "<old_name><digits?>" with "<new_name><(digits or 0)+ofs>"
    # Only matches when old_name is a standalone token prefix (not inside another identifier).
    if not old_name:
        return line  # Avoid infinite loop on empty pattern

    def is_ident_char(ch: str) -> bool:
        # Identifier character: letter, digit, or underscore
        # Explicitly treat predicate prefixes as non-identifier chars
        if ch in ("@", "!"):
            return False
        return is_char_letter(ch) or ch.isdigit() or ch == "_"

    def is_prefix_ok_before_token(pos: int) -> bool:
        # Token is allowed if it's at start, or preceded by a delimiter,
        # or preceded by '@' (e.g. '@P5'), or by '@!' (e.g. '@!P5').
        if pos == 0:
            return True
        prev = line[pos - 1]
        if not is_ident_char(prev):
            return True
        if prev == "@":
            return True
        if prev == "!" and pos >= 2 and line[pos - 2] == "@":
            return True
        return False

    out: list[str] = []
    i = 0
    n = len(line)
    ln = len(old_name)

    while i < n:
        if line.startswith("//", i):
            out.append(line[i:])
            break

        if line.startswith(old_name, i):
            # Ensure we are not in the middle of another identifier
            if is_prefix_ok_before_token(i):
                j = i + ln

                # Case 1: end of string right after name -> treat as index 0
                if j == n:
                    out.append(new_name)
                    out.append(str(ofs))
                    i = j
                    continue

                # Case 2: digits exist -> parse and add offset
                if line[j].isdigit():
                    k = j
                    while k < n and line[k].isdigit():
                        k += 1

                    # If identifier continues (e.g. "Ri8a"), do not treat it as a register
                    if k < n and is_ident_char(line[k]):
                        pass
                    else:
                        old_num = int(line[j:k])
                        new_num = old_num + ofs
                        out.append(new_name)
                        out.append(str(new_num))
                        i = k
                        continue

                # Case 3: no digits -> only accept if token ends here (delimiter)
                else:
                    if not is_ident_char(line[j]):
                        out.append(new_name)
                        out.append(str(ofs))
                        i = j
                        continue

        out.append(line[i])
        i += 1

    return "".join(out)

def get_var_index(s: str) -> tuple[str, int]:
    s = s.strip()
    if not s:
        return ("", 0)
    # First char must be a letter
    c0 = s[0]
    if not (("A" <= c0 <= "Z") or ("a" <= c0 <= "z")):
        return ("", 0)
    # Consume letters at the start (at least one already guaranteed)
    i = 0
    n = len(s)
    while i < n and (("A" <= s[i] <= "Z") or ("a" <= s[i] <= "z")):
        i += 1
    name = s[:i]
    # Now we must see at least one digit, and the rest must be digits only
    if i >= n:
        return ("", 0)
    if not ("0" <= s[i] <= "9"):
        return ("", 0)
    for j in range(i, n):
        if not ("0" <= s[j] <= "9"):
            return ("", 0)
    return (name, int(s[i:]))

def add_label_index(s: str, func_ind: int) -> str:
    # A label is: '.' + at least one letter, then letters/digits/'_'.
    # The '.' is valid only if it is at the start of the string or preceded by '(' or a space.
    suffix = "_" + str(func_ind)
    out: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        if s[i] == "." and (i == 0 or s[i - 1] == "(" or s[i - 1] == " ") and (i + 1) < n:
            c1 = s[i + 1]
            if ("A" <= c1 <= "Z") or ("a" <= c1 <= "z"):
                k = i + 2
                # Consume the rest of the label: letters, digits, underscore
                while k < n:
                    c = s[k]
                    if (("A" <= c <= "Z") or ("a" <= c <= "z") or
                        ("0" <= c <= "9") or (c == "_")):
                        k += 1
                    else:
                        break
                out.append(s[i:k])
                out.append(suffix)
                i = k
                continue
        out.append(s[i])
        i += 1
    return "".join(out)

def get_number_end(s: str) -> int:
    s = s.strip()
    if not s:
        return -1
    # Check last character is a digit
    c = s[-1]
    if not ("0" <= c <= "9"):
        return -1
    # Scan backwards over trailing digits
    i = len(s) - 1
    while i >= 0 and ("0" <= s[i] <= "9"):
        i -= 1
    return int(s[i + 1 :])

def get_cmd_cnt(lines: List[str], start_ind: int, end_ind: int) -> int:
    cnt = 0
    n = len(lines)
    for i in range(start_ind, end_ind):
        s = lines[i].strip()
        if s.startswith("["):
            cnt += 1
    return cnt

def extract_word_and_index(s: str) -> Tuple[str, int]:
    # Split into: <prefix><digits>, where digits start at the first numeric character.
    s = s.strip()
    if not s:
        return ("", 0)
    n = len(s)
    i = 0
    while i < n and not s[i].isdigit():
        i += 1
    # No digits, or name is empty
    if i == 0 or i == n:
        return ("", 0)
    # Ensure the rest is digits only
    j = i
    while j < n and s[j].isdigit():
        j += 1
    if j != n:
        return ("", 0)
    return (s[:i], int(s[i:]))

def process_expressions(line: str, consts: Dict[str, str]) -> str:
    out: list[str] = []
    i = 0
    n = len(line)
    while i < n:
        if line[i] == "{":
            j = line.find("}", i + 1)
            if j == -1:
                # No closing brace: keep the rest as-is
                out.append(line[i:])
                break
            inner = line[i + 1 : j]
            repl = exp.process_exp(inner, consts)
            out.append(repl)
            i = j + 1
            continue
        out.append(line[i])
        i += 1
    return "".join(out)

def remove_comments(lines: List[str]) -> List[str]:
    out: List[str] = []
    in_block = False
    for line in lines:
        i = 0
        n = len(line)
        parts: List[str] = []
        while i < n:
            if in_block:
                # We are inside a /* ... */ block: drop everything until we find */
                end = line.find("*/", i)
                if end == -1:
                    # Whole line is commented out
                    i = n
                    break
                # End of block comment: drop up to and including */
                i = end + 2
                in_block = False
                continue
            # Not in block comment: find next // or /* from position i
            idx_line = line.find("//", i)
            idx_block = line.find("/*", i)
            # If // comes first (or /* not found), cut the rest of the line
            if idx_line != -1 and (idx_block == -1 or idx_line < idx_block):
                parts.append(line[i:idx_line])
                i = n
                break
            # If /* comes first
            if idx_block != -1:
                parts.append(line[i:idx_block])
                end = line.find("*/", idx_block + 2)
                if end == -1:
                    # Multi-line block comment starts: drop the rest of this line
                    in_block = True
                    i = n
                    break
                # Single-line block comment: skip it and continue scanning
                i = end + 2
                continue
            # No more comments on this line
            parts.append(line[i:])
            break
        out.append("".join(parts))
    return out

def PreprocessLines(lines:List[str]) -> List[str]:
    out: List[str] = []
    i = 0
    n = len(lines)
    while i < n:
        s = lines[i].rstrip(" \t")
        # Join continuation lines ending with '\'
        while s.endswith("\\") and (i + 1) < n:
            s = s[:-1]  # remove trailing backslash
            i += 1
            s += lines[i].rstrip(" \t")
        out.append(s)
        i += 1
    return out

def find_exe(exe: str) -> str:
    p = Path(exe)
    # If the exact file exists, return it as-is
    if p.is_file():
        return exe
    # Otherwise, search for any .exe in the same directory
    d = p.parent
    if d.is_dir():
        for entry in d.iterdir():
            if entry.is_file() and entry.suffix.lower() == ".exe":
                return str(entry)
    # Fallback: return the original input
    return exe

def replace_str(s: str, pos: int, substr: str) -> str:
    # Replace part of s starting at pos with substr (overwriting len(substr) chars).
    if pos < 0 or pos > len(s):
        return s
    end = pos + len(substr)
    return s[:pos] + substr + s[end:]

def change_ext(filename: str, new_ext: str) -> str:
    if new_ext and not new_ext.startswith("."):
        new_ext = "." + new_ext
    return str(Path(filename).with_suffix(new_ext))

def copy_file(src: str, dst: str) -> None:
    shutil.copyfile(src, dst)

def delete_file(path: str) -> None:
    os.remove(path)

def rename_file(src: str, dst: str) -> None:
    os.replace(src, dst)

########################################################################################################################
# Numeric token: decimal or hex with 0x prefix (optional sign)
_NUM_TOKEN_RE = re.compile(r'^[+-]?(?:0[xX][0-9a-fA-F]+|\d+)$')

# Full expression: "a <op> b", where a/b are decimal or 0x-hex
_COMP_RE = re.compile(
    r'^\s*([+-]?(?:0[xX][0-9a-fA-F]+|\d+))\s*(>=|<=|==|!=|>|<)\s*([+-]?(?:0[xX][0-9a-fA-F]+|\d+))\s*$'
)

def _parse_int(token: str) -> int:
    # int(x, 0) accepts: 123, 0xFF, 0o77, 0b1010, with optional +/- sign
    return int(token, 0)

def eval_comp(s: str) -> int:
    """
    Evaluate a numeric expression from a string.

    Returns:
        1  -> expression is true (or number is non-zero)
        0  -> expression is false (or number is zero)
        -1 -> parse error / unsupported expression
    """
    if s is None:
        return -1

    s = s.strip()
    if not s:
        return -1

    # Type 1: a single integer (decimal or hex)
    if _NUM_TOKEN_RE.match(s):
        try:
            return 1 if _parse_int(s) != 0 else 0
        except Exception:
            return -1

    # Type 2: "a <op> b"
    m = _COMP_RE.match(s)
    if not m:
        return -1

    try:
        a = _parse_int(m.group(1))
        op = m.group(2)
        b = _parse_int(m.group(3))
    except Exception:
        return -1

    if op == ">":
        return 1 if a > b else 0
    if op == ">=":
        return 1 if a >= b else 0
    if op == "<":
        return 1 if a < b else 0
    if op == "<=":
        return 1 if a <= b else 0
    if op == "==":
        return 1 if a == b else 0
    if op == "!=":
        return 1 if a != b else 0
    return -1

def check_if_else_end(ls: List[str]) -> Optional[List[str]]:
    """
    Process #IF ... #ELSE ... #ENDIF blocks in a list of lines.

    Rules:
    - Lines are matched by stripping spaces and checking startswith("#IF"), "#ELSE"/"#ELSEIF", "#ENDIF".
    - If condition eval_comp(...) == -1 or matching #ENDIF not found -> return None.
    - If condition is true (1): keep THEN part, drop ELSE part (if present) and directives.
    - If condition is false (0): keep ELSE part (if present), otherwise keep nothing; drop directives.

    Notes:
    - Supports nested #IF/#ENDIF by tracking depth.
    - "#ELSEIF" is treated as "#ELSE" (no extra condition handling).
    """
    if ls is None:
        return None

    out = list(ls)  # Do not mutate the input list
    i = 0

    while i < len(out):
        s = out[i].strip()
        if not s.startswith("#IF"):
            i += 1
            continue

        cond_str = s[3:].strip()  # everything after "#IF"
        res = eval_comp(cond_str)
        if res == -1:
            return None

        # Scan forward to find matching #ENDIF (and optional #ELSE at the same nesting level)
        depth = 1
        else_idx = None
        endif_idx = None

        j = i + 1
        while j < len(out):
            sj = out[j].strip()

            if sj.startswith("#IF"):
                depth += 1
            elif sj.startswith("#ENDIF"):
                depth -= 1
                if depth == 0:
                    endif_idx = j
                    break
            elif depth == 1 and else_idx is None and (sj.startswith("#ELSE") or sj.startswith("#ELSEIF")):
                else_idx = j

            j += 1

        if endif_idx is None:
            return None

        # Compute which slice of lines to keep (excluding directives)
        if res == 1:
            # Keep THEN: (i+1 .. else_idx-1) or (i+1 .. endif_idx-1)
            keep_start = i + 1
            keep_end = else_idx if else_idx is not None else endif_idx
            kept = out[keep_start:keep_end]
        else:
            # Keep ELSE: (else_idx+1 .. endif_idx-1), or keep nothing if no else
            if else_idx is None:
                kept = []
            else:
                kept = out[else_idx + 1:endif_idx]

        # Replace whole block [#IF .. #ENDIF] with kept content
        out = out[:i] + kept + out[endif_idx + 1:]

        # After replacement, continue scanning from the same position,
        # because kept content may start with another #IF (nested or subsequent).
        # But avoid infinite loops if kept is empty.
        if not kept:
            # Nothing inserted at i, so move forward.
            # (Still safe: out[i] is now what used to be after #ENDIF.)
            continue

    return out
########################################################################################################################