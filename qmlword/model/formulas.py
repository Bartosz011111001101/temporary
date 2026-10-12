"""Formuły w komórkach tabel (jak pola w edytorach tekstu).

Składnia:  =SUMA(POWYŻEJ)   =ŚREDNIA(B2:B5)   =B2*C2   =ZAOKR(SUMA(LEWO); 1)
Funkcje:   SUMA/SUM, ŚREDNIA/AVERAGE, MIN, MAX, ILE/COUNT, ILOCZYN/PRODUCT, ZAOKR/ROUND
Kierunki:  POWYŻEJ/ABOVE, PONIŻEJ/BELOW, LEWO/LEFT, PRAWO/RIGHT
Odwołania: A1 (kolumna literą, wiersz od 1), zakresy A1:B3. Liczby jak „1 240,50”.
Bez eval – własny parser.
"""
from __future__ import annotations

import math
import re
from typing import Callable

from .blocks import TableData, plain_text

ERROR = "#BŁĄD"

FUNCTIONS: dict[str, str] = {
    "SUM": "sum", "SUMA": "sum",
    "AVERAGE": "avg", "ŚREDNIA": "avg", "SREDNIA": "avg",
    "MIN": "min", "MAX": "max",
    "COUNT": "count", "ILE": "count", "LICZ": "count",
    "PRODUCT": "product", "ILOCZYN": "product",
    "ROUND": "round", "ZAOKR": "round",
}
DIRECTIONS = {
    "ABOVE": "above", "POWYŻEJ": "above", "POWYZEJ": "above",
    "BELOW": "below", "PONIŻEJ": "below", "PONIZEJ": "below",
    "LEFT": "left", "LEWO": "left",
    "RIGHT": "right", "PRAWO": "right",
}

_TOKEN = re.compile(r"\s*(?:(\d+(?:[.,]\d+)?)|([A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż_]+\d*)|(.))")


class FormulaError(Exception):
    pass


def parse_number(text: str) -> float | None:
    t = text.strip().replace(" ", "").replace(" ", "").replace("%", "")
    if not t:
        return None
    if t.count(",") == 1 and "." in t:  # 1.240,50
        t = t.replace(".", "")
    t = t.replace(",", ".")
    try:
        value = float(t)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def format_number(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        text = f"{int(round(value)):,}".replace(",", " ")
        return text
    text = f"{value:,.2f}".replace(",", " ").replace(".", ",")
    return text


def col_index(letters: str) -> int:
    n = 0
    for ch in letters.upper():
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


class _Parser:
    def __init__(self, text: str, cell_value: Callable[[int, int], float | None],
                 direction: Callable[[str], list[float]], rows: int, cols: int) -> None:
        self.tokens = []
        for num, word, sym in _TOKEN.findall(text):
            if num:
                self.tokens.append(("num", float(num.replace(",", "."))))
            elif word:
                self.tokens.append(("word", word.upper()))
            elif sym.strip():
                self.tokens.append(("sym", sym))
        self.i = 0
        self.cell_value = cell_value
        self.direction = direction
        self.rows, self.cols = rows, cols

    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else (None, None)

    def take(self, kind=None, value=None):
        tok = self.peek()
        if tok[0] is None or (kind and tok[0] != kind) or (value is not None and tok[1] != value):
            raise FormulaError("Nieoczekiwany element formuły.")
        self.i += 1
        return tok

    def parse(self) -> float:
        value = self.expr()
        if self.i != len(self.tokens):
            raise FormulaError("Nadmiarowe elementy formuły.")
        return value

    def expr(self) -> float:
        value = self.term()
        while self.peek() in (("sym", "+"), ("sym", "-")):
            op = self.take()[1]
            rhs = self.term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def term(self) -> float:
        value = self.factor()
        while self.peek() in (("sym", "*"), ("sym", "/")):
            op = self.take()[1]
            rhs = self.factor()
            if op == "/" and rhs == 0:
                raise FormulaError("Dzielenie przez zero.")
            value = value * rhs if op == "*" else value / rhs
        return value

    def ref(self, word: str) -> tuple[int, int]:
        m = re.fullmatch(r"([A-Z]+)(\d+)", word)
        if not m:
            raise FormulaError(f"Nieznana nazwa: {word}")
        r, c = int(m.group(2)) - 1, col_index(m.group(1))
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            raise FormulaError("Odwołanie poza tabelą.")
        return r, c

    def factor(self) -> float:
        kind, value = self.peek()
        if kind == "sym" and value == "-":
            self.take()
            return -self.factor()
        if kind == "sym" and value == "(":
            self.take()
            result = self.expr()
            self.take("sym", ")")
            return result
        if kind == "num":
            self.take()
            return value
        if kind == "word":
            self.take()
            if value in FUNCTIONS:
                return self.call(FUNCTIONS[value])
            r, c = self.ref(value)
            v = self.cell_value(r, c)
            return v if v is not None else 0.0
        raise FormulaError("Niepełna formuła.")

    def args(self) -> list[list[float]]:
        self.take("sym", "(")
        groups: list[list[float]] = []
        while True:
            kind, value = self.peek()
            if kind == "word" and value in DIRECTIONS:
                self.take()
                groups.append(self.direction(DIRECTIONS[value]))
            elif kind == "word" and re.fullmatch(r"[A-Z]+\d+", value) \
                    and self.tokens[self.i + 1:self.i + 2] == [("sym", ":")]:
                start = self.ref(self.take()[1])
                self.take("sym", ":")
                end = self.ref(self.take("word")[1])
                vals = []
                for r in range(min(start[0], end[0]), max(start[0], end[0]) + 1):
                    for c in range(min(start[1], end[1]), max(start[1], end[1]) + 1):
                        v = self.cell_value(r, c)
                        if v is not None:
                            vals.append(v)
                groups.append(vals)
            else:
                groups.append([self.expr()])
            if self.peek() in (("sym", ";"), ("sym", ",")):
                self.take()
                continue
            self.take("sym", ")")
            return groups

    def call(self, name: str) -> float:
        groups = self.args()
        values = [v for g in groups for v in g]
        if name == "sum":
            return sum(values)
        if name == "avg":
            if not values:
                raise FormulaError("Brak liczb do średniej.")
            return sum(values) / len(values)
        if name == "min":
            return min(values) if values else 0.0
        if name == "max":
            return max(values) if values else 0.0
        if name == "count":
            return float(len(values))
        if name == "product":
            out = 1.0
            for v in values:
                out *= v
            return out
        if name == "round":
            if len(groups) != 2 or len(groups[0]) != 1:
                raise FormulaError("ZAOKR(liczba; miejsca)")
            return round(groups[0][0], int(groups[1][0]) if groups[1] else 0)
        raise FormulaError("Nieznana funkcja.")


def evaluate(table: TableData, row: int, col: int, formula: str,
             values: dict[tuple[int, int], float | None] | None = None) -> str:
    text = formula.strip()
    if text.startswith("="):
        text = text[1:]
    if not text:
        return ERROR
    cov = table.coverage()

    def cell_value(r: int, c: int) -> float | None:
        ar, ac = cov[r][c]
        if (ar, ac) == (row, col):
            return None
        if values is not None and (ar, ac) in values:
            return values[(ar, ac)]
        return parse_number(plain_text(table.cells[ar][ac].runs))

    def direction(kind: str) -> list[float]:
        coords = []
        if kind == "above":
            first = 1 if table.header_row else 0
            coords = [(r, col) for r in range(first, row)]
        elif kind == "below":
            coords = [(r, col) for r in range(row + 1, table.rows)]
        elif kind == "left":
            coords = [(row, c) for c in range(0, col)]
        elif kind == "right":
            coords = [(row, c) for c in range(col + 1, table.cols)]
        seen, out = set(), []
        for r, c in coords:
            anchor = cov[r][c]
            if anchor in seen:
                continue
            seen.add(anchor)
            v = cell_value(r, c)
            if v is not None:
                out.append(v)
        return out

    try:
        return format_number(_Parser(text, cell_value, direction, table.rows, table.cols).parse())
    except (FormulaError, ValueError, OverflowError, ZeroDivisionError):
        return ERROR
