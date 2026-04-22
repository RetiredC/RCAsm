# This file is a part of RCAsm software
# (c) 2026, RetiredCoder (RC)
# License: GPLv3, see "LICENSE.TXT" file
# https://github.com/RetiredC

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple


# ----------------------------
# Tokenizer
# ----------------------------

@dataclass(frozen=True)
class Token:
    kind: str
    text: str


def _tokenize(expr: str) -> List[Token]:
    tokens: List[Token] = []
    i = 0
    n = len(expr)

    while i < n:
        c = expr[i]

        if c.isspace():
            i += 1
            continue

        # Two-char operators: << and >>
        if c == "<" and i + 1 < n and expr[i + 1] == "<":
            tokens.append(Token("<<", "<<"))
            i += 2
            continue
        if c == ">" and i + 1 < n and expr[i + 1] == ">":
            tokens.append(Token(">>", ">>"))
            i += 2
            continue

        # One-char operators
        if c in "+-*/()":
            tokens.append(Token(c, c))
            i += 1
            continue

        # Number: starts with digit, allow alnum and '_' tail for 0xFF, 0b1010, 123_456
        if "0" <= c <= "9":
            j = i + 1
            while j < n and (expr[j].isalnum() or expr[j] == "_"):
                j += 1
            tokens.append(Token("NUM", expr[i:j]))
            i = j
            continue

        # Identifier: starts with letter or underscore, then letters/digits/underscore
        if ("A" <= c <= "Z") or ("a" <= c <= "z") or (c == "_"):
            j = i + 1
            while j < n and (expr[j].isalnum() or expr[j] == "_"):
                j += 1
            tokens.append(Token("ID", expr[i:j]))
            i = j
            continue

        # Unknown character
        tokens.append(Token("BAD", c))
        i += 1

    return tokens


# ----------------------------
# AST
# ----------------------------

class Node:
    pass


@dataclass(frozen=True)
class Const(Node):
    value: int


@dataclass(frozen=True)
class Sym(Node):
    name: str


@dataclass(frozen=True)
class Unary(Node):
    op: str  # only "-"
    expr: Node


@dataclass(frozen=True)
class Bin(Node):
    op: str  # "+", "-", "*", "/", "<<", ">>"
    left: Node
    right: Node


class ParseError(Exception):
    pass


# ----------------------------
# Parser (recursive descent)
# Precedence: unary > * / > + - > << >>
# ----------------------------

class _Parser:
    def __init__(self, tokens: List[Token]):
        self.toks = tokens
        self.i = 0

    def _peek(self) -> Optional[Token]:
        return None if self.i >= len(self.toks) else self.toks[self.i]

    def _accept(self, kind: str) -> Optional[Token]:
        t = self._peek()
        if t and t.kind == kind:
            self.i += 1
            return t
        return None

    def _expect(self, kind: str) -> Token:
        t = self._accept(kind)
        if not t:
            raise ParseError(f"Expected {kind} at token index {self.i}")
        return t

    def parse(self) -> Node:
        node = self._shift()
        if self._peek() is not None:
            raise ParseError("Trailing tokens")
        return node

    # shift := add (('<<'|'>>') add)*
    def _shift(self) -> Node:
        node = self._add()
        while True:
            t = self._peek()
            if t and t.kind in ("<<", ">>"):
                self.i += 1
                right = self._add()
                node = Bin(t.kind, node, right)
            else:
                break
        return node

    # add := mul (('+'|'-') mul)*
    def _add(self) -> Node:
        node = self._mul()
        while True:
            t = self._peek()
            if t and t.kind in ("+", "-"):
                self.i += 1
                right = self._mul()
                node = Bin(t.kind, node, right)
            else:
                break
        return node

    # mul := factor (('*'|'/') factor)*
    def _mul(self) -> Node:
        node = self._factor()
        while True:
            t = self._peek()
            if t and t.kind in ("*", "/"):
                self.i += 1
                right = self._factor()
                node = Bin(t.kind, node, right)
            else:
                break
        return node

    # factor := ('+'|'-') factor | primary
    def _factor(self) -> Node:
        t = self._peek()
        if t and t.kind in ("+", "-"):
            self.i += 1
            inner = self._factor()
            if t.kind == "+":
                return inner
            return Unary("-", inner)
        return self._primary()

    # primary := NUMBER | IDENT | '(' shift ')'
    def _primary(self) -> Node:
        t = self._peek()
        if t is None:
            raise ParseError("Unexpected end of expression")

        if t.kind == "NUM":
            self.i += 1
            try:
                return Const(int(t.text, 0))  # base 0 supports 0x.., 0b.., and underscores
            except Exception as e:
                raise ParseError(f"Bad number: {t.text}") from e

        if t.kind == "ID":
            self.i += 1
            return Sym(t.text)

        if t.kind == "(":
            self.i += 1
            node = self._shift()
            self._expect(")")
            return node

        raise ParseError(f"Unexpected token: {t.kind}:{t.text}")


# ----------------------------
# Expand consts + simplify
# ----------------------------

def _int_div_trunc(a: int, b: int) -> int:
    # Truncate toward zero (C-like), without floats
    if b == 0:
        raise ZeroDivisionError
    q = abs(a) // abs(b)
    return -q if (a < 0) ^ (b < 0) else q


def _expand_consts(node: Node, consts: Dict[str, str], visiting: Set[str]) -> Node:
    if isinstance(node, Sym):
        name = node.name
        if name in consts and name not in visiting:
            visiting.add(name)
            try:
                return _parse_expand_simplify(consts[name], consts, visiting)
            finally:
                visiting.remove(name)
        return node

    if isinstance(node, Const):
        return node

    if isinstance(node, Unary):
        return Unary(node.op, _expand_consts(node.expr, consts, visiting))

    if isinstance(node, Bin):
        return Bin(
            node.op,
            _expand_consts(node.left, consts, visiting),
            _expand_consts(node.right, consts, visiting),
        )

    return node


def _flatten_add(node: Node) -> List[Tuple[int, Node]]:
    if isinstance(node, Bin) and node.op == "+":
        return _flatten_add(node.left) + _flatten_add(node.right)

    if isinstance(node, Bin) and node.op == "-":
        res = _flatten_add(node.left)
        for sgn, term in _flatten_add(node.right):
            res.append((-sgn, term))
        return res

    if isinstance(node, Unary) and node.op == "-":
        res: List[Tuple[int, Node]] = []
        for sgn, term in _flatten_add(node.expr):
            res.append((-sgn, term))
        return res

    return [(1, node)]


def _build_add(terms: List[Tuple[int, Node]]) -> Node:
    s0, n0 = terms[0]
    expr: Node = n0 if s0 > 0 else Unary("-", n0)
    for sgn, term in terms[1:]:
        expr = Bin("+", expr, term) if sgn > 0 else Bin("-", expr, term)
    return expr


def _flatten_mul(node: Node) -> List[Node]:
    if isinstance(node, Bin) and node.op == "*":
        return _flatten_mul(node.left) + _flatten_mul(node.right)
    return [node]


def _build_mul(factors: List[Node]) -> Node:
    expr = factors[0]
    for f in factors[1:]:
        expr = Bin("*", expr, f)
    return expr


def _simplify(node: Node) -> Node:
    if isinstance(node, (Const, Sym)):
        return node

    if isinstance(node, Unary):
        inner = _simplify(node.expr)
        if isinstance(inner, Const):
            return Const(-inner.value)
        if isinstance(inner, Unary) and inner.op == "-":
            return _simplify(inner.expr)
        return Unary("-", inner)

    if isinstance(node, Bin):
        left = _simplify(node.left)
        right = _simplify(node.right)
        op = node.op

        if op in ("+", "-"):
            tmp = Bin(op, left, right)
            terms = [(sgn, _simplify(term)) for sgn, term in _flatten_add(tmp)]

            const_sum = 0
            kept: List[Tuple[int, Node]] = []
            for sgn, term in terms:
                if isinstance(term, Const):
                    const_sum += sgn * term.value
                else:
                    kept.append((sgn, term))

            if not kept:
                return Const(const_sum)

            if const_sum != 0:
                kept.append((-1, Const(-const_sum)) if const_sum < 0 else (1, Const(const_sum)))

            kept = [(sgn, term) for sgn, term in kept if not (isinstance(term, Const) and term.value == 0)]

            if len(kept) == 1:
                sgn, term = kept[0]
                return term if sgn > 0 else _simplify(Unary("-", term))

            return _build_add(kept)

        if op == "*":
            factors = [_simplify(f) for f in _flatten_mul(Bin("*", left, right))]
            prod = 1
            nonconst: List[Node] = []
            for f in factors:
                if isinstance(f, Const):
                    prod *= f.value
                else:
                    nonconst.append(f)

            if prod == 0:
                return Const(0)
            if not nonconst:
                return Const(prod)
            if prod == 1:
                return nonconst[0] if len(nonconst) == 1 else _build_mul(nonconst)
            if prod == -1:
                mul = nonconst[0] if len(nonconst) == 1 else _build_mul(nonconst)
                return _simplify(Unary("-", mul))

            # Put the combined constant at the end (keeps "SYM * 0x2" style)
            nonconst.append(Const(prod))
            return nonconst[0] if len(nonconst) == 1 else _build_mul(nonconst)

        if op == "/":
            if isinstance(left, Const) and isinstance(right, Const):
                if right.value == 0:
                    return Bin("/", left, right)
                return Const(_int_div_trunc(left.value, right.value))

            if isinstance(left, Const) and left.value == 0:
                return Const(0)
            if isinstance(right, Const) and right.value == 1:
                return left

            return Bin("/", left, right)

        if op in ("<<", ">>"):
            # Fold if both sides are constants (and shift count is valid)
            if isinstance(right, Const):
                if right.value == 0:
                    return left
                if right.value < 0:
                    return Bin(op, left, right)

                if isinstance(left, Const):
                    try:
                        if op == "<<":
                            return Const(left.value << right.value)
                        return Const(left.value >> right.value)
                    except Exception:
                        return Bin(op, left, right)

                # 0 << x == 0 and 0 >> x == 0 when x is known non-negative
                if isinstance(left, Const) and left.value == 0:
                    return Const(0)

            return Bin(op, left, right)

    return node


def _parse_expand_simplify(expr: str, consts: Dict[str, str], visiting: Set[str]) -> Node:
    toks = _tokenize(expr)
    for t in toks:
        if t.kind == "BAD":
            raise ParseError(f"Bad character: {t.text}")

    node = _Parser(toks).parse()
    node = _expand_consts(node, consts, visiting)
    node = _simplify(node)
    return node


# ----------------------------
# Stringify (hex output)
# ----------------------------

def _prec(node: Node) -> int:
    if isinstance(node, Bin):
        if node.op in ("<<", ">>"):
            return 0
        if node.op in ("+", "-"):
            return 1
        if node.op in ("*", "/"):
            return 2
        return 0
    if isinstance(node, Unary):
        return 3
    return 4


def _fmt_hex(v: int) -> str:
    # Format integer as hex with 0x prefix; keep sign outside.
    if v < 0:
        return "-0x" + format(-v, "X")
    return "0x" + format(v, "X")


def _to_string(node: Node, parent_prec: int = 0) -> str:
    if isinstance(node, Const):
        return _fmt_hex(node.value)

    if isinstance(node, Sym):
        return node.name

    if isinstance(node, Unary):
        inner = _to_string(node.expr, 3)
        if _prec(node.expr) < 3:
            inner = f"({inner})"
        return "-" + inner

    if isinstance(node, Bin):
        p = _prec(node)
        left_s = _to_string(node.left, p)
        right_s = _to_string(node.right, p)

        # Parenthesize right operand when needed for correct associativity/precedence
        if isinstance(node.right, (Bin, Unary)):
            rp = _prec(node.right)
            if rp < p or (rp == p and node.op in ("-", "/", "<<", ">>")):
                right_s = f"({right_s})"

        s = f"{left_s} {node.op} {right_s}"
        if p < parent_prec:
            return f"({s})"
        return s

    raise TypeError("Unknown node type")


# ----------------------------
# Public API
# ----------------------------

def process_exp(s: str, consts: Dict[str, str]) -> str:
    s = s.strip()
    if not s:
        return ""

    try:
        node = _parse_expand_simplify(s, consts, set())
        node = _simplify(node)
        return _to_string(node)
    except Exception:
        # If parsing fails, return original expression unchanged
        return s
