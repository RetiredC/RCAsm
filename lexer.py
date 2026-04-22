# This file is a part of RCAsm software
# (c) 2026, RetiredCoder (RC)
# License: GPLv3, see "LICENSE.TXT" file
# https://github.com/RetiredC

from PyQt5.Qsci import QsciLexerCustom
from PyQt5.QtGui import QColor, QFont
from PyQt5.Qsci import QsciScintillaBase

class AsmLexer(QsciLexerCustom):
    # Style ids (0..)
    DEFAULT   = 0
    MNEMO     = 1
    REG       = 2
    NUMBER    = 3
    LABEL     = 4
    DIRECTIVE = 5
    COMMENT   = 6
    SPECIAL   = 7  # call_func / inc_func

    _SPECIAL_WORDS = {"call_func", "inc_func", "include", "FUNCTION", "KERNEL", "INCLUDE", "CONST"}

    def __init__(self, parent=None, font: QFont | None = None):
        super().__init__(parent)
        self._font = font or QFont("Consolas", 11)

    def language(self) -> str:
        return "ASM"

    def description(self, style: int) -> str:
        return {
            self.DEFAULT: "Default",
            self.MNEMO: "Mnemonic",
            self.REG: "Register",
            self.NUMBER: "Number",
            self.LABEL: "Label",
            self.DIRECTIVE: "Directive",
            self.COMMENT: "Comment",
            self.SPECIAL: "Special word",
        }.get(style, "")

    def defaultFont(self, style: int) -> QFont:
        return self._font

    def defaultPaper(self, style: int) -> QColor:
        return QColor(200, 200, 200)

    def defaultColor(self, style: int) -> QColor:
        if style == self.MNEMO:
            return QColor(0, 0, 180)
        if style == self.REG:
            return QColor(140, 0, 140)
        if style == self.NUMBER:
            return QColor(0, 120, 0)
        if style == self.LABEL:
            return QColor(160, 80, 0)
        if style == self.DIRECTIVE:
            return QColor(0, 120, 120)
        if style == self.COMMENT:
            return QColor(110, 110, 110)
        if style == self.SPECIAL:
            return QColor(180, 0, 0)
        return QColor(0, 0, 0)

    @staticmethod
    def _is_reg(w: str) -> bool:
        # Pseudo registers with index
        if w.startswith("Rt") and w[2:].isdigit():
            return True
        if w.startswith("Rtt") and w[3:].isdigit():
            return True
        if w.startswith("Ri") and w[2:].isdigit():
            return True
        if w.startswith("Rii") and w[3:].isdigit():
            return True
        if w.startswith("Ro") and w[2:].isdigit():
            return True
        if w.startswith("Roo") and w[3:].isdigit():
            return True
        if w.startswith("URt") and w[3:].isdigit():
            return True
        if w.startswith("URi") and w[3:].isdigit():
            return True
        if w.startswith("URo") and w[3:].isdigit():
            return True
        if w.startswith("Pt") and w[2:].isdigit():
            return True
        if w.startswith("Pi") and w[2:].isdigit():
            return True
        if w.startswith("Po") and w[2:].isdigit():
            return True
        # Canonical special regs
        if w in ("RZ", "URZ", "PT"):
            return True
        # Numbered regs
        if w.startswith("UR") and w[2:].isdigit():
            return True
        if w.startswith("R") and w[1:].isdigit():
            return True
        if w.startswith("P") and w[1:].isdigit():
            return True
        if w.startswith("UP") and w[2:].isdigit():
            return True
        return False

    @staticmethod
    def _is_number(w: str) -> bool:
        if not w:
            return False
        if w[0] in "+-" and len(w) > 1:
            w2 = w[1:]
        else:
            w2 = w

        if w2.startswith(("0x", "0X")):
            if len(w2) <= 2:
                return False
            for ch in w2[2:]:
                if ch not in "0123456789abcdefABCDEF":
                    return False
            return True

        if w2.startswith(("0b", "0B")):
            if len(w2) <= 2:
                return False
            for ch in w2[2:]:
                if ch not in "01":
                    return False
            return True

        return w2.isdigit()

    @staticmethod
    def _apply_style(style_arr: list[int], a: int, b: int, style: int) -> None:
        n = len(style_arr)
        a = max(0, min(a, n))
        b = max(0, min(b, n))
        for i in range(a, b):
            style_arr[i] = style

    def styleText(self, start: int, end: int) -> None:
        ed = self.editor()
        if ed is None:
            return

        bse = QsciScintillaBase

        start_line, _ = ed.lineIndexFromPosition(start)
        end_line, _ = ed.lineIndexFromPosition(end)

        start_pos = ed.positionFromLineIndex(start_line, 0)
        self.startStyling(start_pos)

        # Bit 0 of line state means "inside /* ... */ at end of this line"
        IN_BLOCK_BIT = 1

        for line in range(start_line, end_line + 1):
            text = ed.text(line) or ""
            n = len(text)

            if n == 0:
                # Preserve block-comment state across empty lines
                in_block = False
                if line > 0:
                    prev_state = ed.SendScintilla(bse.SCI_GETLINESTATE, line - 1)
                    in_block = bool(prev_state & IN_BLOCK_BIT)
                ed.SendScintilla(bse.SCI_SETLINESTATE, line, IN_BLOCK_BIT if in_block else 0)
                continue

            styles = [self.DEFAULT] * n

            # Determine if we start this line inside a block comment
            in_block = False
            if line > 0:
                prev_state = ed.SendScintilla(bse.SCI_GETLINESTATE, line - 1)
                in_block = bool(prev_state & IN_BLOCK_BIT)

            # Collect comment spans (start, end) where end is exclusive
            comment_spans: List[Tuple[int, int]] = []
            pos = 0

            while pos < n:
                if in_block:
                    end_pos = text.find("*/", pos)
                    if end_pos == -1:
                        comment_spans.append((pos, n))
                        pos = n
                        break
                    comment_spans.append((pos, end_pos + 2))
                    pos = end_pos + 2
                    in_block = False
                    continue

                idx_line = text.find("//", pos)
                idx_block = text.find("/*", pos)

                if idx_line == -1 and idx_block == -1:
                    break

                # Pick the earliest comment start
                if idx_line != -1 and (idx_block == -1 or idx_line < idx_block):
                    comment_spans.append((idx_line, n))
                    pos = n
                    break

                # Block comment starts
                end_pos = text.find("*/", idx_block + 2)
                if end_pos == -1:
                    comment_spans.append((idx_block, n))
                    in_block = True
                    pos = n
                    break
                comment_spans.append((idx_block, end_pos + 2))
                pos = end_pos + 2

            # Store block-comment state for the next line
            ed.SendScintilla(bse.SCI_SETLINESTATE, line, IN_BLOCK_BIT if in_block else 0)

            # Apply COMMENT style spans
            for a, b in comment_spans:
                self._apply_style(styles, a, b, self.COMMENT)

            # Build code segments (outside comments)
            code_segments: List[Tuple[int, int]] = []
            cur = 0
            for a, b in comment_spans:
                if cur < a:
                    code_segments.append((cur, a))
                cur = max(cur, b)
            if cur < n:
                code_segments.append((cur, n))

            # Highlight the first token in the first non-empty code segment
            first_done = False
            for seg_start, seg_end in code_segments:
                i = seg_start
                while i < seg_end and text[i].isspace():
                    i += 1
                if i >= seg_end:
                    continue

                j = i
                while j < seg_end and (not text[j].isspace()) and text[j] != ",":
                    j += 1
                first = text[i:j]

                if first in self._SPECIAL_WORDS:
                    self._apply_style(styles, i, j, self.SPECIAL)
                elif first.endswith(":") and first:
                    self._apply_style(styles, i, j, self.LABEL)
                elif first.startswith(".") and first:
                    self._apply_style(styles, i, j, self.DIRECTIVE)
                elif first.startswith("["):
                    self._apply_style(styles, i, j, self.MNEMO)

                first_done = True
                break

            # Highlight registers, numbers, and special words in code segments only
            for seg_start, seg_end in code_segments:
                k = seg_start
                while k < seg_end:
                    c = text[k]

                    if c.isalnum() or c == "_":
                        a = k
                        k += 1
                        while k < seg_end and (text[k].isalnum() or text[k] == "_"):
                            k += 1
                        w = text[a:k]

                        if w in self._SPECIAL_WORDS:
                            self._apply_style(styles, a, k, self.SPECIAL)
                        elif self._is_reg(w):
                            self._apply_style(styles, a, k, self.REG)
                        elif self._is_number(w):
                            self._apply_style(styles, a, k, self.NUMBER)

                    elif c in "+-":
                        a = k
                        k += 1
                        b = k
                        while b < seg_end and (text[b].isalnum() or text[b] == "_"):
                            b += 1
                        w = text[a:b]
                        if self._is_number(w):
                            self._apply_style(styles, a, b, self.NUMBER)
                        k = b
                    else:
                        k += 1

            # Emit styling runs for the whole line
            run_style = styles[0]
            run_len = 1
            for idx in range(1, n):
                if styles[idx] == run_style:
                    run_len += 1
                else:
                    self.setStyling(run_len, run_style)
                    run_style = styles[idx]
                    run_len = 1
            self.setStyling(run_len, run_style)


