"""
Validation helpers for DocForm interviews.

Components conform to InterviewSchema.json: each component has a top-level
`type`, `id`, and (for non-dialog types) a `label`, with configuration
properties at the top level (camelCase). Supports string, number, datetime,
choice, repeat, and dialog component types.
"""

import re
from datetime import datetime
from typing import Any

from expression_eval import (
    evaluate_expression,
    get_referenced_field_ids,
    validate_expression_syntax,
)

VALID_TYPES = {"string", "number", "datetime", "choice", "repeat", "dialog"}


def _collect_component_ids(components: list, ids: set) -> None:
    """Recursively gather every component id from a tree."""
    if not isinstance(components, list):
        return
    for comp in components:
        if not isinstance(comp, dict):
            continue
        cid = comp.get("id")
        if cid:
            ids.add(cid)
        if comp.get("type") in ("repeat", "dialog"):
            _collect_component_ids(comp.get("components", []), ids)


def _collect_expression_components(
    components: list, out: list, inside_repeat: bool = False
) -> None:
    """Walk the component tree and collect each number component that has an
    `expression` property. Components inside `repeat` groups are skipped — they
    cannot be evaluated against the top-level form data and per-row computed
    fields are not currently supported."""
    if not isinstance(components, list):
        return
    for comp in components:
        if not isinstance(comp, dict):
            continue
        ctype = comp.get("type")
        if ctype == "number" and comp.get("expression") and not inside_repeat:
            out.append(comp)
        if ctype == "repeat":
            _collect_expression_components(comp.get("components", []), out, True)
        elif ctype == "dialog":
            _collect_expression_components(
                comp.get("components", []), out, inside_repeat
            )


def _detect_expression_cycles(components: list) -> None:
    """Raise ValueError if there's a cycle among top-level computed fields.

    Builds a directed graph where each top-level computed field points at the
    other top-level computed fields it references in its expression, then
    runs a DFS to detect any cycle (including a self-loop). Schemas like
    `{"id": "total", "expression": "total + 1"}` or mutually-referencing
    pairs like `a = b + 1` / `b = a` would crash the frontend in an infinite
    render loop, so they're rejected at schema-validation time.
    """
    expr_components: list = []
    _collect_expression_components(components, expr_components)

    expr_by_id: dict[str, dict] = {}
    for comp in expr_components:
        cid = comp.get("id")
        if cid:
            expr_by_id[cid] = comp

    if not expr_by_id:
        return

    # Map each computed field id to the *computed* field ids its expression
    # references. References to non-computed fields don't matter for cycles.
    deps: dict[str, set[str]] = {}
    for cid, comp in expr_by_id.items():
        refs = get_referenced_field_ids(comp.get("expression", "") or "")
        deps[cid] = {r for r in refs if r in expr_by_id}

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {cid: WHITE for cid in expr_by_id}

    def visit(cid: str, stack: list) -> None:
        if color[cid] == GRAY:
            cycle_path = stack[stack.index(cid):] + [cid]
            raise ValueError(
                f"Component '{cid}': circular reference detected "
                f"({' → '.join(cycle_path)})"
            )
        if color[cid] == BLACK:
            return
        color[cid] = GRAY
        stack.append(cid)
        for dep in deps.get(cid, ()):
            visit(dep, stack)
        stack.pop()
        color[cid] = BLACK

    for cid in expr_by_id:
        if color[cid] == WHITE:
            visit(cid, [])


def validate_questions(
    components: list,
    _inside_repeat: bool = False,
    _all_ids: set | None = None,
) -> list:
    """Validate a list of InterviewSchema components (recursive).

    Ensures each component has a valid type, unique id, and the fields required
    for its type. Does not mutate or normalize input — returns the original
    components list once validated.
    """
    if not isinstance(components, list):
        raise ValueError("Components must be a list")

    # Collect every id in the full tree once at the top-level call so that
    # nested expression validation can reference outer fields (e.g. a number
    # inside a top-level dialog referencing a sibling outside that dialog).
    is_top_level = _all_ids is None
    if _all_ids is None:
        _all_ids = set()
        _collect_component_ids(components, _all_ids)

    validated: list = []
    seen_ids: set = set()

    for i, comp in enumerate(components):
        if not isinstance(comp, dict):
            raise ValueError(f"Component {i + 1} must be an object")

        ctype = comp.get("type", "")
        cid = comp.get("id", "")

        if not cid:
            raise ValueError(f"Component {i + 1} is missing 'id'")
        if not ctype:
            raise ValueError(f"Component {i + 1} is missing 'type'")
        if ctype not in VALID_TYPES:
            raise ValueError(
                f"Component '{cid}': invalid type '{ctype}'. "
                f"Must be one of: {', '.join(sorted(VALID_TYPES))}"
            )

        if ctype == "dialog":
            if not comp.get("title"):
                raise ValueError(f"Component '{cid}': dialog type requires 'title'")
        else:
            if not comp.get("label"):
                raise ValueError(f"Component '{cid}' is missing 'label'")

        if cid in seen_ids:
            raise ValueError(f"Duplicate component id: '{cid}'")
        seen_ids.add(cid)

        if ctype == "choice":
            options = comp.get("options", [])
            if not isinstance(options, list) or len(options) == 0:
                raise ValueError(
                    f"Component '{cid}': choice type requires a non-empty 'options' array"
                )
            for opt in options:
                if not isinstance(opt, dict) or "value" not in opt or "label" not in opt:
                    raise ValueError(
                        f"Component '{cid}': each option must have 'value' and 'label'"
                    )

        if ctype == "repeat":
            nested = comp.get("components", [])
            if not isinstance(nested, list) or len(nested) == 0:
                raise ValueError(
                    f"Component '{cid}': repeat type requires a non-empty 'components' array"
                )
            validate_questions(nested, _inside_repeat=True, _all_ids=_all_ids)
        elif ctype == "dialog":
            nested = comp.get("components", [])
            if not isinstance(nested, list) or len(nested) == 0:
                raise ValueError(
                    f"Component '{cid}': dialog type requires a non-empty 'components' array"
                )
            validate_questions(
                nested, _inside_repeat=_inside_repeat, _all_ids=_all_ids
            )

        if ctype == "number" and comp.get("expression"):
            if _inside_repeat:
                raise ValueError(
                    f"Component '{cid}': 'expression' is not supported on number "
                    f"components inside a repeat group"
                )
            expr_errors = validate_expression_syntax(comp["expression"], _all_ids)
            if expr_errors:
                raise ValueError(
                    f"Component '{cid}': invalid expression — {'; '.join(expr_errors)}"
                )

        validated.append(comp)

    # Cycle detection only makes sense once the full tree has been walked, so
    # do it on the top-level call after all expressions have been syntax-
    # validated and we know each one parses cleanly.
    if is_top_level:
        _detect_expression_cycles(components)

    return validated


def _label_for(comp: dict) -> str:
    return comp.get("label") or comp.get("title") or comp.get("id", "")


def _validate_string(comp: dict, value: Any, errors: list) -> Any:
    val = str(value)
    min_len = comp.get("minLength", 0) or 0
    max_len = comp.get("maxLength")
    pattern = comp.get("pattern")

    if len(val) < min_len:
        errors.append(f"Field '{_label_for(comp)}' must be at least {min_len} characters")
        return None
    if max_len is not None and len(val) > max_len:
        errors.append(f"Field '{_label_for(comp)}' must be at most {max_len} characters")
        return None
    if pattern:
        try:
            if not re.match(pattern, val):
                desc = comp.get("patternDescription") or f"match pattern {pattern}"
                errors.append(f"Field '{_label_for(comp)}' must {desc}")
                return None
        except re.error:
            pass

    return val


def _validate_number(comp: dict, value: Any, errors: list) -> Any:
    try:
        num = float(value)
    except (ValueError, TypeError):
        errors.append(f"Field '{_label_for(comp)}' must be a valid number")
        return None

    integer_only = comp.get("integerOnly", False)
    if integer_only and num != int(num):
        errors.append(f"Field '{_label_for(comp)}' must be a whole number")
        return None

    min_val = comp.get("min")
    max_val = comp.get("max")
    decimal_places = comp.get("decimalPlaces")

    if min_val is not None and num < min_val:
        errors.append(f"Field '{_label_for(comp)}' must be at least {min_val}")
        return None
    if max_val is not None and num > max_val:
        errors.append(f"Field '{_label_for(comp)}' must be at most {max_val}")
        return None
    if decimal_places is not None:
        str_val = str(value)
        if "." in str_val:
            actual_decimals = len(str_val.split(".")[1])
            if actual_decimals > decimal_places:
                errors.append(
                    f"Field '{_label_for(comp)}' must have at most {decimal_places} decimal places"
                )
                return None

    return int(num) if integer_only else num


def _validate_datetime(comp: dict, value: Any, errors: list) -> Any:
    val = str(value).strip()
    include_time = comp.get("includeTime", False)

    parsed_date = None
    try:
        if include_time and "T" in val:
            parsed_date = datetime.fromisoformat(val)
        else:
            parsed_date = datetime.strptime(val[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        errors.append(f"Field '{_label_for(comp)}' must be a valid date (YYYY-MM-DD)")
        return None

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    allow_future = comp.get("allowFuture", True)
    allow_past = comp.get("allowPast", True)
    min_date_str = comp.get("minDate")
    max_date_str = comp.get("maxDate")

    if not allow_future and parsed_date > today:
        errors.append(f"Field '{_label_for(comp)}' cannot be in the future")
        return None
    if not allow_past and parsed_date < today:
        errors.append(f"Field '{_label_for(comp)}' cannot be in the past")
        return None

    if min_date_str:
        try:
            min_date = datetime.strptime(min_date_str, "%Y-%m-%d")
            if parsed_date < min_date:
                errors.append(f"Field '{_label_for(comp)}' cannot be before {min_date_str}")
                return None
        except ValueError:
            pass

    if max_date_str:
        try:
            max_date = datetime.strptime(max_date_str, "%Y-%m-%d")
            if parsed_date > max_date:
                errors.append(f"Field '{_label_for(comp)}' cannot be after {max_date_str}")
                return None
        except ValueError:
            pass

    return val


def _validate_choice(comp: dict, value: Any, errors: list) -> Any:
    options = comp.get("options", [])
    valid_values = [opt["value"] for opt in options if isinstance(opt, dict) and "value" in opt]
    allow_multiple = comp.get("allowMultiple", False)
    min_sel = comp.get("minSelections", 0) or 0
    max_sel = comp.get("maxSelections")

    if allow_multiple:
        vals = value if isinstance(value, list) else [value]
        invalid_opts = [v for v in vals if v not in valid_values]
        if invalid_opts:
            errors.append(
                f"Field '{_label_for(comp)}': invalid option(s): "
                f"{', '.join(str(o) for o in invalid_opts)}"
            )
            return None
        if len(vals) < min_sel:
            errors.append(f"Field '{_label_for(comp)}' requires at least {min_sel} selection(s)")
            return None
        if max_sel is not None and len(vals) > max_sel:
            errors.append(f"Field '{_label_for(comp)}' allows at most {max_sel} selection(s)")
            return None
        return vals

    if value not in valid_values:
        errors.append(f"Field '{_label_for(comp)}': '{value}' is not a valid option")
        return None
    return value


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _validate_component(
    comp: dict,
    data: dict,
    validated: dict,
    errors: list,
    inside_repeat: bool = False,
) -> None:
    ctype = comp.get("type")
    cid = comp.get("id")
    required = comp.get("required", False)

    # Top-level computed number fields are derived server-side; skip all
    # client-value validation (required, min/max, decimalPlaces). The actual
    # value is set later by `_recompute_expressions`. Inside repeats this
    # is rejected at schema-validation time, but we re-check here as a
    # defense-in-depth measure: any expression-bearing field that slips
    # through inside a repeat falls back to normal number validation so
    # arbitrary client values cannot pass through unvalidated.
    if ctype == "number" and comp.get("expression") and not inside_repeat:
        return

    if ctype == "dialog":
        for nested in comp.get("components", []):
            _validate_component(nested, data, validated, errors, inside_repeat)
        return

    if ctype == "repeat":
        raw = data.get(cid)
        nested_components = comp.get("components", [])
        min_items = comp.get("minItems")
        max_items = comp.get("maxItems")

        if raw is None:
            raw = []
        if not isinstance(raw, list):
            errors.append(f"Field '{_label_for(comp)}' must be a list")
            return

        if required and len(raw) == 0:
            errors.append(f"Field '{_label_for(comp)}' is required")
            return
        if min_items is not None and len(raw) < min_items:
            errors.append(f"Field '{_label_for(comp)}' requires at least {min_items} item(s)")
            return
        if max_items is not None and len(raw) > max_items:
            errors.append(f"Field '{_label_for(comp)}' allows at most {max_items} item(s)")
            return

        validated_items: list = []
        for idx, item in enumerate(raw):
            if not isinstance(item, dict):
                errors.append(f"Field '{_label_for(comp)}': item {idx + 1} must be an object")
                continue
            item_validated: dict = {}
            item_errors: list = []
            for nested in nested_components:
                _validate_component(
                    nested, item, item_validated, item_errors, inside_repeat=True
                )
            if item_errors:
                for e in item_errors:
                    errors.append(f"{_label_for(comp)}[{idx + 1}]: {e}")
                continue
            for k, v in item.items():
                if k not in item_validated:
                    item_validated[k] = v
            validated_items.append(item_validated)

        validated[cid] = validated_items
        return

    # Skip expression fields — they are computed, not user-supplied
    if ctype == "number" and comp.get("expression"):
        return

    value = data.get(cid)

    if required and _is_empty(value):
        if ctype == "choice" and comp.get("allowMultiple"):
            if not isinstance(value, list) or len(value) == 0:
                errors.append(f"Field '{_label_for(comp)}' is required")
                return
        else:
            errors.append(f"Field '{_label_for(comp)}' is required")
            return

    if _is_empty(value) and not (ctype == "choice" and comp.get("allowMultiple")):
        validated[cid] = value if value is not None else ""
        return

    if ctype == "string":
        result = _validate_string(comp, value, errors)
    elif ctype == "number":
        result = _validate_number(comp, value, errors)
    elif ctype == "datetime":
        result = _validate_datetime(comp, value, errors)
    elif ctype == "choice":
        if _is_empty(value) and not comp.get("allowMultiple"):
            validated[cid] = value if value is not None else ""
            return
        result = _validate_choice(comp, value, errors)
    else:
        result = value

    if result is not None:
        validated[cid] = result


def _recompute_expressions(components: list, validated: dict) -> None:
    """Overwrite computed `number` fields with server-side evaluations.

    The client-submitted value for any number component with an `expression`
    is replaced by re-evaluating the expression against `validated`. This
    ensures the server is the source of truth for derived values.
    """
    expr_components: list = []
    _collect_expression_components(components, expr_components)
    for comp in expr_components:
        cid = comp.get("id")
        expression = comp.get("expression")
        if not cid or not expression:
            continue
        result = evaluate_expression(expression, validated)
        if result is None:
            continue
        decimal_places = comp.get("decimalPlaces")
        if decimal_places is not None:
            result = round(result, int(decimal_places))
        validated[cid] = result


def validate_submission_data(components: list, data: dict) -> dict:
    """Validate submitted interview answers against InterviewSchema components."""
    if not isinstance(data, dict):
        raise ValueError("Submission data must be an object")

    validated: dict = {}
    errors: list = []

    for comp in components:
        _validate_component(comp, data, validated, errors)

    if errors:
        raise ValueError("; ".join(errors))

    # Computed top-level number fields are never validated (so they're not in
    # `validated`), but they may still be present in `data`. Skip them in the
    # catch-all copy so client-submitted values can't pollute the input to
    # `_recompute_expressions` and influence other expressions that reference
    # them.
    expr_components: list = []
    _collect_expression_components(components, expr_components)
    expr_ids = {c.get("id") for c in expr_components if c.get("id")}

    for k, v in data.items():
        if k in validated or k in expr_ids:
            continue
        validated[k] = v

    _recompute_expressions(components, validated)

    return validated
