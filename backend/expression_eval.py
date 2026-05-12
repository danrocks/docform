"""Safe expression evaluator for computed interview fields.

Supports:
    - Arithmetic: +, -, *, /
    - Numeric literals: 42, 3.14
    - Field references: field_id (top-level), group.child (repeat-group member)
    - Aggregate functions over repeat groups:
        sum(group.field)            — sum of a single field
        sum(group.a * group.b)      — sum of per-row products
        count(group)                — number of items
        avg(group.field)            — average
        min(group.field)            — minimum
        max(group.field)            — maximum
    - Parentheses for grouping
    - round(expr, digits)           — round to N decimal places

All evaluation is done via a recursive-descent parser — no eval().
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Tokeniser
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(
    r"""
    (\d+(?:\.\d+)?)      |  # number literal
    ([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*)  |  # identifier / dotted ref
    ([+\-*/(),])            # operator / punctuation
    """,
    re.VERBOSE,
)

_TOK_NUM = "NUM"
_TOK_ID = "ID"
_TOK_OP = "OP"

_AGGREGATES = {"sum", "count", "avg", "min", "max"}
_FUNCTIONS = _AGGREGATES | {"round"}


def _tokenise(expr: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    for m in _TOKEN_RE.finditer(expr):
        if m.group(1):
            tokens.append((_TOK_NUM, m.group(1)))
        elif m.group(2):
            tokens.append((_TOK_ID, m.group(2)))
        elif m.group(3):
            tokens.append((_TOK_OP, m.group(3)))
    return tokens


# ---------------------------------------------------------------------------
# Parser  (recursive-descent, produces an AST)
# ---------------------------------------------------------------------------

class _Parser:
    """Recursive-descent parser producing a simple AST."""

    def __init__(self, tokens: list[tuple[str, str]]) -> None:
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> tuple[str, str] | None:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _advance(self) -> tuple[str, str]:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _expect(self, kind: str, value: str | None = None) -> tuple[str, str]:
        tok = self._peek()
        if tok is None:
            raise ExpressionError(f"Unexpected end of expression, expected {value or kind}")
        if tok[0] != kind or (value is not None and tok[1] != value):
            raise ExpressionError(f"Expected '{value or kind}', got '{tok[1]}'")
        return self._advance()

    # expr  -> term (('+' | '-') term)*
    def parse_expr(self) -> dict:
        node = self._parse_term()
        while True:
            tok = self._peek()
            if tok and tok[0] == _TOK_OP and tok[1] in ("+", "-"):
                op = self._advance()[1]
                right = self._parse_term()
                node = {"op": op, "left": node, "right": right}
            else:
                break
        return node

    # term  -> unary (('*' | '/') unary)*
    def _parse_term(self) -> dict:
        node = self._parse_unary()
        while True:
            tok = self._peek()
            if tok and tok[0] == _TOK_OP and tok[1] in ("*", "/"):
                op = self._advance()[1]
                right = self._parse_unary()
                node = {"op": op, "left": node, "right": right}
            else:
                break
        return node

    # unary -> '-' unary | atom
    def _parse_unary(self) -> dict:
        tok = self._peek()
        if tok and tok[0] == _TOK_OP and tok[1] == "-":
            self._advance()
            operand = self._parse_unary()
            return {"op": "neg", "operand": operand}
        return self._parse_atom()

    # atom  -> NUMBER | function_call | identifier | '(' expr ')'
    def _parse_atom(self) -> dict:
        tok = self._peek()
        if tok is None:
            raise ExpressionError("Unexpected end of expression")

        if tok[0] == _TOK_NUM:
            self._advance()
            return {"lit": float(tok[1])}

        if tok[0] == _TOK_ID:
            name = tok[1]
            self._advance()
            # Check if it's a function call
            nxt = self._peek()
            if nxt and nxt[0] == _TOK_OP and nxt[1] == "(":
                if name not in _FUNCTIONS:
                    raise ExpressionError(f"Unknown function '{name}'")
                self._advance()  # consume '('
                if name == "count":
                    # count(group) — argument is a single identifier
                    arg_tok = self._expect(_TOK_ID)
                    self._expect(_TOK_OP, ")")
                    return {"func": "count", "group": arg_tok[1]}
                elif name == "round":
                    # round(expr, digits)
                    arg = self.parse_expr()
                    self._expect(_TOK_OP, ",")
                    digits_tok = self._expect(_TOK_NUM)
                    self._expect(_TOK_OP, ")")
                    return {"func": "round", "arg": arg, "digits": int(float(digits_tok[1]))}
                else:
                    # sum/avg/min/max — argument is an expression (parsed in aggregate context)
                    arg = self.parse_expr()
                    self._expect(_TOK_OP, ")")
                    return {"func": name, "arg": arg}
            # Plain identifier (field reference)
            return {"ref": name}

        if tok[0] == _TOK_OP and tok[1] == "(":
            self._advance()
            node = self.parse_expr()
            self._expect(_TOK_OP, ")")
            return node

        raise ExpressionError(f"Unexpected token '{tok[1]}'")


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

class ExpressionError(Exception):
    """Raised for malformed or unevaluable expressions."""


def _to_number(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def _resolve_ref(ref: str, data: dict) -> Any:
    """Resolve a dotted reference against the submission data.

    - ``total_price``       → ``data["total_price"]``
    - ``actions.unit_price``→ raises — only valid inside an aggregate
    """
    if "." in ref:
        raise ExpressionError(
            f"Dotted reference '{ref}' can only be used inside an aggregate function "
            f"like sum(), avg(), etc."
        )
    return data.get(ref)


def _collect_groups(node: dict) -> set[str]:
    """Walk an AST node and return the set of repeat-group names referenced via dot notation."""
    groups: set[str] = set()
    if "ref" in node:
        if "." in node["ref"]:
            groups.add(node["ref"].split(".")[0])
    elif "left" in node:
        groups |= _collect_groups(node["left"])
        groups |= _collect_groups(node["right"])
    elif "operand" in node:
        groups |= _collect_groups(node["operand"])
    elif "arg" in node and isinstance(node["arg"], dict):
        groups |= _collect_groups(node["arg"])
    return groups


def _eval_row(node: dict, row: dict, data: dict) -> float:
    """Evaluate an AST node in the context of a single repeat-group row."""
    if "lit" in node:
        return node["lit"]

    if "ref" in node:
        ref = node["ref"]
        if "." in ref:
            _group, field = ref.split(".", 1)
            return _to_number(row.get(field))
        return _to_number(data.get(ref))

    if "op" in node:
        op = node["op"]
        if op == "neg":
            return -_eval_row(node["operand"], row, data)
        left = _eval_row(node["left"], row, data)
        right = _eval_row(node["right"], row, data)
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left / right if right != 0 else 0.0

    if "func" in node:
        return _eval_node(node, data)

    raise ExpressionError(f"Cannot evaluate node: {node}")


def _eval_node(node: dict, data: dict) -> float:
    """Evaluate an AST node against the full submission data."""
    if "lit" in node:
        return node["lit"]

    if "ref" in node:
        return _to_number(_resolve_ref(node["ref"], data))

    if "op" in node:
        op = node["op"]
        if op == "neg":
            return -_eval_node(node["operand"], data)
        left = _eval_node(node["left"], data)
        right = _eval_node(node["right"], data)
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left / right if right != 0 else 0.0

    if "func" in node:
        func = node["func"]

        if func == "count":
            group_name = node["group"]
            items = data.get(group_name, [])
            return float(len(items) if isinstance(items, list) else 0)

        if func == "round":
            val = _eval_node(node["arg"], data)
            return round(val, node["digits"])

        # Aggregate: sum, avg, min, max
        arg = node["arg"]
        groups = _collect_groups(arg)
        if not groups:
            raise ExpressionError(
                f"{func}() requires a repeat-group reference (e.g. {func}(group.field))"
            )
        if len(groups) > 1:
            raise ExpressionError(
                f"{func}() references multiple groups: {groups}. Only one is allowed."
            )
        group_name = groups.pop()
        items = data.get(group_name, [])
        if not isinstance(items, list):
            items = []

        if len(items) == 0:
            return 0.0

        values = [_eval_row(arg, row, data) for row in items]

        if func == "sum":
            return sum(values)
        if func == "avg":
            return sum(values) / len(values)
        if func == "min":
            return min(values)
        if func == "max":
            return max(values)

    raise ExpressionError(f"Cannot evaluate node: {node}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_expression(expr: str) -> dict:
    """Parse an expression string into an AST."""
    tokens = _tokenise(expr)
    if not tokens:
        raise ExpressionError("Empty expression")
    parser = _Parser(tokens)
    ast = parser.parse_expr()
    if parser.pos < len(parser.tokens):
        raise ExpressionError(
            f"Unexpected token '{parser.tokens[parser.pos][1]}' after expression"
        )
    return ast


def evaluate_expression(expr: str, data: dict) -> float:
    """Parse and evaluate an expression against submission data.

    Returns the computed numeric result.
    """
    ast = parse_expression(expr)
    return _eval_node(ast, data)


def evaluate_computed_fields(components: list, data: dict) -> dict:
    """Evaluate all computed (expression) fields and return an updated data dict.

    Iterates components (including nested ones) looking for number fields
    with an ``expression`` property.  Computed values are injected into a
    *copy* of *data* so they are available for docx rendering and
    subsequent expressions.
    """
    result = dict(data)
    _eval_components(components, result)
    return result


def _eval_components(components: list, data: dict) -> None:
    """Recursively evaluate expression fields in component list."""
    for comp in components:
        ctype = comp.get("type", "")
        if ctype in ("dialog", "repeat"):
            nested = comp.get("components", [])
            if ctype == "dialog":
                _eval_components(nested, data)
            # For repeat groups, evaluate expressions inside each row
            if ctype == "repeat":
                group_id = comp.get("id", "")
                items = data.get(group_id, [])
                if isinstance(items, list):
                    for row in items:
                        _eval_components(nested, {**data, **row})
                        # Write computed values back into the row
                        for child in nested:
                            if child.get("type") == "number" and child.get("expression"):
                                row[child["id"]] = evaluate_expression(
                                    child["expression"], {**data, **row}
                                )
        elif ctype == "number" and comp.get("expression"):
            field_id = comp["id"]
            try:
                data[field_id] = evaluate_expression(comp["expression"], data)
            except ExpressionError:
                pass  # leave as-is if expression can't be evaluated
