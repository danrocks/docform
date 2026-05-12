"""
Expression parser and evaluator for computed `number` components.

Used to evaluate the `expression` property on number components in interview
schemas. Supports a small grammar with arithmetic, field references, and
aggregate functions over arrays from repeat groups.

Grammar:
    expression     = additive
    additive       = multiplicative ( ("+" | "-") multiplicative )*
    multiplicative = unary ( ("*" | "/") unary )*
    unary          = "-" unary | primary
    primary        = NUMBER | FUNCTION "(" argument ")" | field_ref | "(" expression ")"
    field_ref      = IDENTIFIER ( "." IDENTIFIER )?
    FUNCTION       = "sum" | "count" | "avg" | "min" | "max"

Field references resolve against the form `data` object:
    `field_id`            -> data["field_id"]
    `repeat_id.field_id`  -> [item["field_id"] for item in data["repeat_id"]]
    `repeat_id` (in count) -> data["repeat_id"]

Evaluation rules:
    - Missing/empty values are treated as 0
    - Division by zero returns 0
    - No `eval()` is ever used; expressions are parsed and walked explicitly
"""

from __future__ import annotations

from typing import Any

AGGREGATE_FUNCTIONS = {"sum", "count", "avg", "min", "max"}


class ExpressionError(ValueError):
    """Raised for parse/syntax errors in an expression."""


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

# Token kinds: NUMBER, IDENT, OP, LPAREN, RPAREN, COMMA, DOT, EOF
class _Token:
    __slots__ = ("kind", "value", "pos")

    def __init__(self, kind: str, value: Any, pos: int) -> None:
        self.kind = kind
        self.value = value
        self.pos = pos


def _tokenize(expr: str) -> list[_Token]:
    tokens: list[_Token] = []
    i = 0
    n = len(expr)
    while i < n:
        c = expr[i]
        if c.isspace():
            i += 1
            continue
        if c.isdigit() or (c == "." and i + 1 < n and expr[i + 1].isdigit()):
            start = i
            seen_dot = False
            while i < n and (expr[i].isdigit() or (expr[i] == "." and not seen_dot)):
                if expr[i] == ".":
                    seen_dot = True
                i += 1
            tokens.append(_Token("NUMBER", float(expr[start:i]), start))
            continue
        if c.isalpha() or c == "_":
            start = i
            while i < n and (expr[i].isalnum() or expr[i] == "_"):
                i += 1
            tokens.append(_Token("IDENT", expr[start:i], start))
            continue
        if c in "+-*/":
            tokens.append(_Token("OP", c, i))
            i += 1
            continue
        if c == "(":
            tokens.append(_Token("LPAREN", c, i))
            i += 1
            continue
        if c == ")":
            tokens.append(_Token("RPAREN", c, i))
            i += 1
            continue
        if c == ",":
            tokens.append(_Token("COMMA", c, i))
            i += 1
            continue
        if c == ".":
            tokens.append(_Token("DOT", c, i))
            i += 1
            continue
        raise ExpressionError(f"Unexpected character '{c}' at position {i}")
    tokens.append(_Token("EOF", None, n))
    return tokens


# ---------------------------------------------------------------------------
# AST nodes (plain dicts to keep things simple)
# ---------------------------------------------------------------------------
#   {"type": "num", "value": float}
#   {"type": "binop", "op": "+|-|*|/", "left": node, "right": node}
#   {"type": "neg", "operand": node}
#   {"type": "field", "path": [str, ...]}
#   {"type": "call", "name": str, "arg": node}


# ---------------------------------------------------------------------------
# Parser (recursive descent)
# ---------------------------------------------------------------------------

class _Parser:
    def __init__(self, tokens: list[_Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> _Token:
        return self.tokens[self.pos]

    def consume(self) -> _Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, kind: str, value: Any = None) -> _Token:
        tok = self.peek()
        if tok.kind != kind or (value is not None and tok.value != value):
            expected = kind if value is None else f"{kind} '{value}'"
            raise ExpressionError(
                f"Expected {expected} at position {tok.pos}, got {tok.kind} '{tok.value}'"
            )
        return self.consume()

    def parse(self) -> dict:
        node = self.parse_expression()
        if self.peek().kind != "EOF":
            tok = self.peek()
            raise ExpressionError(
                f"Unexpected token '{tok.value}' at position {tok.pos}"
            )
        return node

    def parse_expression(self) -> dict:
        return self.parse_additive()

    def parse_additive(self) -> dict:
        node = self.parse_multiplicative()
        while self.peek().kind == "OP" and self.peek().value in ("+", "-"):
            op = self.consume().value
            right = self.parse_multiplicative()
            node = {"type": "binop", "op": op, "left": node, "right": right}
        return node

    def parse_multiplicative(self) -> dict:
        node = self.parse_unary()
        while self.peek().kind == "OP" and self.peek().value in ("*", "/"):
            op = self.consume().value
            right = self.parse_unary()
            node = {"type": "binop", "op": op, "left": node, "right": right}
        return node

    def parse_unary(self) -> dict:
        if self.peek().kind == "OP" and self.peek().value == "-":
            self.consume()
            return {"type": "neg", "operand": self.parse_unary()}
        if self.peek().kind == "OP" and self.peek().value == "+":
            self.consume()
            return self.parse_unary()
        return self.parse_primary()

    def parse_primary(self) -> dict:
        tok = self.peek()
        if tok.kind == "NUMBER":
            self.consume()
            return {"type": "num", "value": tok.value}
        if tok.kind == "LPAREN":
            self.consume()
            node = self.parse_expression()
            self.expect("RPAREN")
            return node
        if tok.kind == "IDENT":
            name = self.consume().value
            if self.peek().kind == "LPAREN":
                if name not in AGGREGATE_FUNCTIONS:
                    raise ExpressionError(
                        f"Unknown function '{name}' at position {tok.pos}"
                    )
                self.consume()
                arg = self.parse_expression()
                self.expect("RPAREN")
                return {"type": "call", "name": name, "arg": arg}
            path = [name]
            while self.peek().kind == "DOT":
                self.consume()
                next_tok = self.expect("IDENT")
                path.append(next_tok.value)
            return {"type": "field", "path": path}
        raise ExpressionError(
            f"Unexpected token '{tok.value}' at position {tok.pos}"
        )


def _parse(expr: str) -> dict:
    if not isinstance(expr, str) or not expr.strip():
        raise ExpressionError("Expression must be a non-empty string")
    tokens = _tokenize(expr)
    return _Parser(tokens).parse()


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def _coerce_number(v: Any) -> float:
    """Coerce a value to a float. Missing/empty/non-numeric values become 0."""
    if v is None:
        return 0.0
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return 0.0
        try:
            return float(s)
        except ValueError:
            return 0.0
    return 0.0


def _resolve_field(path: list[str], data: dict) -> Any:
    """Resolve a field reference against the form data.

    - `[name]`            -> data[name]            (scalar) or list (repeat)
    - `[repeat, child]`   -> [item.child for item in data[repeat]]
    - Missing keys yield None for scalars, [] for repeat-child arrays.
    """
    if not path:
        return None

    if not isinstance(data, dict):
        return None

    if len(path) == 1:
        return data.get(path[0])

    head = path[0]
    rest = path[1:]
    container = data.get(head)
    if container is None:
        return []
    if isinstance(container, list):
        result: list[Any] = []
        for item in container:
            if isinstance(item, dict):
                cur: Any = item
                for key in rest:
                    if isinstance(cur, dict):
                        cur = cur.get(key)
                    else:
                        cur = None
                        break
                result.append(cur)
            else:
                result.append(None)
        return result
    if isinstance(container, dict):
        cur = container
        for key in rest:
            if isinstance(cur, dict):
                cur = cur.get(key)
            else:
                return None
        return cur
    return None


def _to_array(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _eval_node(node: dict, data: dict) -> Any:
    t = node["type"]

    if t == "num":
        return node["value"]

    if t == "neg":
        v = _eval_node(node["operand"], data)
        if isinstance(v, list):
            return [-_coerce_number(x) for x in v]
        return -_coerce_number(v)

    if t == "binop":
        left = _eval_node(node["left"], data)
        right = _eval_node(node["right"], data)
        return _apply_binop(node["op"], left, right)

    if t == "field":
        return _resolve_field(node["path"], data)

    if t == "call":
        arg = _eval_node(node["arg"], data)
        return _apply_aggregate(node["name"], arg)

    raise ExpressionError(f"Unknown node type: {t}")


def _apply_binop(op: str, left: Any, right: Any) -> Any:
    left_is_arr = isinstance(left, list)
    right_is_arr = isinstance(right, list)
    if left_is_arr or right_is_arr:
        if left_is_arr and right_is_arr:
            length = min(len(left), len(right))
            return [_scalar_op(op, left[i], right[i]) for i in range(length)]
        if left_is_arr:
            return [_scalar_op(op, x, right) for x in left]
        return [_scalar_op(op, left, x) for x in right]
    return _scalar_op(op, left, right)


def _scalar_op(op: str, a: Any, b: Any) -> float:
    x = _coerce_number(a)
    y = _coerce_number(b)
    if op == "+":
        return x + y
    if op == "-":
        return x - y
    if op == "*":
        return x * y
    if op == "/":
        if y == 0:
            return 0.0
        return x / y
    raise ExpressionError(f"Unknown operator: {op}")


def _apply_aggregate(name: str, arg: Any) -> float:
    items = _to_array(arg)
    nums = [_coerce_number(v) for v in items]

    if name == "count":
        return float(len(items))
    if not nums:
        return 0.0
    if name == "sum":
        return float(sum(nums))
    if name == "avg":
        return float(sum(nums) / len(nums))
    if name == "min":
        return float(min(nums))
    if name == "max":
        return float(max(nums))
    raise ExpressionError(f"Unknown function: {name}")


def evaluate_expression(expression: str, data: dict) -> float | None:
    """Parse and evaluate `expression` against `data`.

    Returns the numeric result, or None if the expression cannot be parsed.
    Missing fields, division by zero, and non-numeric values are handled
    gracefully (treated as 0); they do not raise.
    """
    try:
        ast = _parse(expression)
    except ExpressionError:
        return None
    if not isinstance(data, dict):
        data = {}
    result = _eval_node(ast, data)
    if isinstance(result, list):
        # Element-wise arithmetic at the top level falls back to sum-style
        # behaviour is NOT implied; we coerce to a single number by summing
        # so that an expression like `items.qty * items.price` (without an
        # outer sum()) still yields a number rather than a list.  However,
        # aggregate functions are the recommended way to collapse arrays.
        return float(sum(_coerce_number(x) for x in result))
    return float(_coerce_number(result))


# ---------------------------------------------------------------------------
# Syntax validation
# ---------------------------------------------------------------------------

def _collect_field_refs(node: dict, refs: list[list[str]]) -> None:
    t = node["type"]
    if t == "field":
        refs.append(node["path"])
    elif t == "neg":
        _collect_field_refs(node["operand"], refs)
    elif t == "binop":
        _collect_field_refs(node["left"], refs)
        _collect_field_refs(node["right"], refs)
    elif t == "call":
        _collect_field_refs(node["arg"], refs)


def validate_expression_syntax(expression: str, known_field_ids: set) -> list[str]:
    """Validate an expression's syntax and field references.

    Returns a list of error messages; empty list means the expression is valid.
    `known_field_ids` should contain all valid component ids (top-level and
    nested inside repeat/dialog) that the expression may reference. Every
    segment of a dotted reference (e.g. `items.price` -> `items` and `price`)
    must exist as some component id; otherwise a typo like `items.pricce`
    silently evaluates to 0.
    """
    errors: list[str] = []
    if not isinstance(expression, str) or not expression.strip():
        errors.append("Expression must be a non-empty string")
        return errors

    try:
        ast = _parse(expression)
    except ExpressionError as exc:
        errors.append(str(exc))
        return errors

    refs: list[list[str]] = []
    _collect_field_refs(ast, refs)
    for path in refs:
        for segment in path:
            if segment not in known_field_ids:
                errors.append(f"Unknown field reference: '{'.'.join(path)}'")
                break
    return errors


def get_referenced_field_ids(expression: str) -> set[str]:
    """Return the set of head field IDs referenced by an expression.

    For dotted refs like `items.price`, only the head segment (`items`) is
    returned — that's the dependency unit that matters for cycle detection
    among top-level computed fields. Returns an empty set if the expression
    cannot be parsed.
    """
    try:
        ast = _parse(expression)
    except ExpressionError:
        return set()
    refs: list[list[str]] = []
    _collect_field_refs(ast, refs)
    return {p[0] for p in refs if p}
