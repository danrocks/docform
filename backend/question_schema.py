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

VALID_TYPES = {"string", "number", "datetime", "choice", "repeat", "dialog"}


def validate_questions(components: list) -> list:
    """Validate a list of InterviewSchema components (recursive).

    Ensures each component has a valid type, unique id, and the fields required
    for its type. Does not mutate or normalize input — returns the original
    components list once validated.
    """
    if not isinstance(components, list):
        raise ValueError("Components must be a list")

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

        if ctype in ("repeat", "dialog"):
            nested = comp.get("components", [])
            if not isinstance(nested, list) or len(nested) == 0:
                raise ValueError(
                    f"Component '{cid}': {ctype} type requires a non-empty 'components' array"
                )
            validate_questions(nested)

        validated.append(comp)

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


def _validate_component(comp: dict, data: dict, validated: dict, errors: list) -> None:
    ctype = comp.get("type")
    cid = comp.get("id")
    required = comp.get("required", False)

    if ctype == "dialog":
        for nested in comp.get("components", []):
            _validate_component(nested, data, validated, errors)
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
                _validate_component(nested, item, item_validated, item_errors)
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

    for k, v in data.items():
        if k not in validated:
            validated[k] = v

    return validated
