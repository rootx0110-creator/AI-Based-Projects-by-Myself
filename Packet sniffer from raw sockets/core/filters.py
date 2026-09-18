"""core/filters.py — display filtering (layer L3).

Supports a Wireshark-like subset:
    tcp.port == 443
    ip.src == 10.0.0.5 and udp
    not icmp or ip.dst == 192.168.1.1
Compiled once into a predicate; applied per packet in O(1).
Unknown tokens never crash: they are treated as no-ops.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from core.packets import Packet

__all__ = ["DisplayFilter", "compile_filter"]

_TOKEN = re.compile(
    r"""(?x)
      (?P<ws>\s+)
    | (?P<op>==|!=|>=|<=|>|<)
    | (?P<and>\band\b|&&)
    | (?P<or>\bor\b|\|\|)
    | (?P<not>\bnot\b|!)
    | (?P<word>[A-Za-z_][A-Za-z0-9_.]*)
    | (?P<val>[0-9][A-Za-z0-9_.:]*|0x[0-9A-Fa-f]+)
    | (?P<bad>.)
    """,
    re.VERBOSE,
)

_FIELDS = {
    "ip.src": "src_ip", "ip.dst": "dst_ip", "ip.ttl": "ttl",
    "tcp.srcport": "src_port", "tcp.dstport": "dst_port",
    "udp.srcport": "src_port", "udp.dstport": "dst_port",
    "tcp.port": "port", "udp.port": "port",
    "tcp.flags": "flags", "proto": "protocol", "frame.len": "length",
}

_ALIASES = {
    "src": "src_ip", "dst": "dst_ip", "srcport": "src_port",
    "dstport": "dst_port", "port": "port", "ttl": "ttl",
    "flags": "flags", "protocol": "protocol", "length": "length",
    "len": "length", "proto": "protocol",
}

_OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
}


def _field_name(word: str) -> str:
    w = word.lower()
    return _FIELDS.get(w) or _ALIASES.get(w, w)


def _as_num(v: str) -> float | None:
    try:
        return float(v)
    except ValueError:
        return None


def _as_ip_tuple(v: str) -> tuple[int, ...] | None:
    parts = v.split(".")
    if len(parts) == 4:
        try:
            return tuple(int(x) for x in parts)
        except ValueError:
            return None
    return None


class _Parser:
    """Recursive-descent parser: or-expr -> and-expr -> not -> atom."""

    def __init__(self, text: str) -> None:
        self.toks: list[tuple[str, str]] = []
        for m in _TOKEN.finditer(text):
            kind = m.lastgroup or "bad"
            if kind == "ws":
                continue
            self.toks.append((kind, m.group(kind)))
        self.i = 0

    def _peek(self) -> tuple[str, str] | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def _match(self, kind: str) -> bool:
        tok = self._peek()
        if tok and tok[0] == kind:
            self.i += 1
            return True
        return False

    def parse(self):
        return self._or()

    def _or(self):
        node = self._and()
        while self._match("or"):
            node = ("or", node, self._and())
        return node

    def _and(self):
        node = self._not()
        while self._match("and"):
            node = ("and", node, self._not())
        return node

    def _not(self):
        if self._match("not"):
            return ("not", self._not())
        return self._atom()

    def _atom(self):
        tok = self._peek()
        if tok is None:
            return ("true",)
        kind, val = tok
        self.i += 1
        if kind == "word":
            low = val.lower()
            if low in ("tcp", "udp", "icmp", "other"):
                return ("proto_is", low)
            if low == "false":
                return ("false",)
            if low == "true":
                return ("true",)
            nxt = self._peek()
            if nxt and nxt[0] == "op":
                op = nxt[1]
                self.i += 1
                vtok = self._peek()
                if vtok is None or vtok[0] not in ("val", "word", "num"):
                    return ("true",)
                self.i += 1
                return ("cmp", _field_name(low), op, vtok[1])
            return ("true",)          # bare unknown word → no-op
        return ("true",)              # numbers, ops, stray chars → no-op


def _cmp(field: str, op: str, raw: str, pkt: Packet) -> bool:
    if field == "port":                     # matches either src or dst port
        n = _as_num(raw)
        if n is not None:
            either = (pkt.src_port == n) or (pkt.dst_port == n)
            if op == "==":
                return either
            if op == "!=":
                return not either
            return False        # ordering on "either port" is ambiguous
    actual = getattr(pkt, field, None)
    if actual is None:
        return False
    fn = _OPS.get(op, _OPS["=="])
    if isinstance(actual, (int, float)):
        n = _as_num(raw)
        if n is not None:
            return fn(actual, n)
    a, b = str(actual).lower(), raw.lower()
    if op in ("==", "!="):
        ai, bi = _as_ip_tuple(a), _as_ip_tuple(b)
        if ai and bi:
            return (ai == bi) if op == "==" else (ai != bi)
    return fn(a, b)


def _eval(node, pkt: Packet) -> bool:
    kind = node[0]
    if kind == "true":
        return True
    if kind == "false":
        return False
    if kind == "and":
        return _eval(node[1], pkt) and _eval(node[2], pkt)
    if kind == "or":
        return _eval(node[1], pkt) or _eval(node[2], pkt)
    if kind == "not":
        return not _eval(node[1], pkt)
    if kind == "proto_is":
        return pkt.protocol.lower() == node[1]
    if kind == "cmp":
        return _cmp(node[1], node[2], node[3], pkt)
    return True


@dataclass
class DisplayFilter:
    text: str = ""
    error: str | None = None

    def __post_init__(self) -> None:
        self._ast = None
        if self.text:
            self.set(self.text)

    def set(self, text: str) -> bool:
        """Compile new filter text. Returns True when it parses cleanly."""
        self.text = (text or "").strip()
        self.error = None
        self._ast = None
        if not self.text:
            return True
        try:
            self._ast = _Parser(self.text).parse()
            return True
        except Exception as exc:
            self.error = str(exc)
            return False

    @property
    def active(self) -> bool:
        return self._ast is not None

    def match(self, pkt: Packet) -> bool:
        return _eval(self._ast, pkt) if self._ast is not None else True


def compile_filter(text: str) -> DisplayFilter:
    return DisplayFilter(text=text)
