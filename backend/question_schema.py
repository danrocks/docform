"""
Canonical question schema for DocForm interviews.

Defines the 4 question types (string, number, date, multiplechoice),
their default configs, and validation functions.
"""

import re
from datetime import datetime, date
from typing import Any

VALID_TYPES = {"string", "number", "date", "multiplechoice"}

DEFAULT_CONFIGS = {
    "string": {
        "min_length": 0,
        "max_length": None,
        "multiline": False,
        "pattern": None,
        "pattern_description": None,
    },
    "number": {
        "min": None,
        "max": None,
        "integer_only": False,
        "decimal_places": None,
        "step": None,
        "unit": None,
    },
    "date": {
        "format": "YYYY-MM-DD",
        "min_date": None,
        "max_date": None,
        "allow_future": True,
        "allow_past": True,
        "include_time": False,
    },
    "multiplechoice": {
        "options": [],
        "allow_multiple": False,
        "min_selections": 0,
        "max_selections": None,
        "display_as": "dropdown",
    },
}


def validate_questions(questions: list) -> list:
    """
    Validate and normalize a list of interview questions.

    - Checks each question has key, label, type
    - Validates type is one of the 4 valid types
    - Merges provided config with defaults for that type
    - For multiplechoice, validates options is a non-empty list
    - Returns normalized questions list with all config defaults filled in
    - Raises ValueError with a clear message if validation fails
    """
    if not isinstance(questions, list):
        raise ValueError("Questions must be a list")

    normalized = []
    seen_keys = set()

    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            raise ValueError(f"Question {i + 1} must be an object")

        # Required fields
        if not q.get("key"):
            raise ValueError(f"Question {i + 1} is missing 'key'")
        if not q.get("label"):
            raise ValueError(f"Question {i + 1} is missing 'label'")
        if not q.get("type"):
            raise ValueError(f"Question {i + 1} is missing 'type'")

        key = str(q["key"]).strip()
        label = str(q["label"]).strip()
        qtype = str(q["type"]).strip().lower()

        if qtype not in VALID_TYPES:
            raise ValueError(
                f"Question {i + 1} ('{key}'): invalid type '{qtype}'. "
                f"Must be one of: {', '.join(sorted(VALID_TYPES))}"
            )

        if key in seen_keys:
            raise ValueError(f"Duplicate question key: '{key}'")
        seen_keys.add(key)

        # Merge config with defaults
        default_config = DEFAULT_CONFIGS[qtype].copy()
        provided_config = q.get("config", {})
        if isinstance(provided_config, dict):
            for k, v in provided_config.items():
                if k in default_config:
                    default_config[k] = v
        config = default_config

        # Type-specific validation
        if qtype == "multiplechoice":
            if not isinstance(config["options"], list) or len(config["options"]) == 0:
                raise ValueError(
                    f"Question '{key}': multiplechoice type requires a non-empty 'options' list in config"
                )
            if config["display_as"] not in ("dropdown", "radio", "checkboxes"):
                raise ValueError(
                    f"Question '{key}': display_as must be 'dropdown', 'radio', or 'checkboxes'"
                )

        normalized.append({
            "key": key,
            "label": label,
            "type": qtype,
            "required": q.get("required", True),
            "placeholder": q.get("placeholder", ""),
            "help_text": q.get("help_text", ""),
            "config": config,
        })

    return normalized


def validate_submission_data(questions: list, data: dict) -> dict:
    """
    Validate submitted interview answers against question configs.

    Returns validated/coerced data dict or raises ValueError.
    """
    if not isinstance(data, dict):
        raise ValueError("Submission data must be an object")

    validated = {}
    errors = []

    for q in questions:
        key = q["key"]
        qtype = q["type"]
        config = q.get("config", {})
        required = q.get("required", True)
        value = data.get(key)

        # Check required
        if required:
            if value is None or (isinstance(value, str) and value.strip() == ""):
                if qtype == "multiplechoice" and config.get("allow_multiple"):
                    if not isinstance(value, list) or len(value) == 0:
                        errors.append(f"Field '{q['label']}' is required")
                        continue
                else:
                    errors.append(f"Field '{q['label']}' is required")
                    continue

        # Skip validation if value is empty and not required
        if value is None or (isinstance(value, str) and value.strip() == ""):
            validated[key] = value if value is not None else ""
            continue

        # Type-specific validation
        if qtype == "string":
            val = str(value)
            min_len = config.get("min_length", 0) or 0
            max_len = config.get("max_length")
            pattern = config.get("pattern")

            if len(val) < min_len:
                errors.append(
                    f"Field '{q['label']}' must be at least {min_len} characters"
                )
                continue
            if max_len is not None and len(val) > max_len:
                errors.append(
                    f"Field '{q['label']}' must be at most {max_len} characters"
                )
                continue
            if pattern:
                try:
                    if not re.match(pattern, val):
                        desc = config.get("pattern_description") or f"match pattern {pattern}"
                        errors.append(f"Field '{q['label']}' must {desc}")
                        continue
                except re.error:
                    pass  # Skip invalid regex patterns

            validated[key] = val

        elif qtype == "number":
            try:
                num = float(value)
            except (ValueError, TypeError):
                errors.append(f"Field '{q['label']}' must be a valid number")
                continue

            integer_only = config.get("integer_only", False)
            if integer_only and num != int(num):
                errors.append(f"Field '{q['label']}' must be a whole number")
                continue

            min_val = config.get("min")
            max_val = config.get("max")
            decimal_places = config.get("decimal_places")

            if min_val is not None and num < min_val:
                errors.append(f"Field '{q['label']}' must be at least {min_val}")
                continue
            if max_val is not None and num > max_val:
                errors.append(f"Field '{q['label']}' must be at most {max_val}")
                continue
            if decimal_places is not None:
                str_val = str(value)
                if "." in str_val:
                    actual_decimals = len(str_val.split(".")[1])
                    if actual_decimals > decimal_places:
                        errors.append(
                            f"Field '{q['label']}' must have at most {decimal_places} decimal places"
                        )
                        continue

            validated[key] = int(num) if integer_only else num

        elif qtype == "date":
            val = str(value).strip()
            include_time = config.get("include_time", False)

            # Parse the date
            parsed_date = None
            try:
                if include_time and "T" in val:
                    parsed_date = datetime.fromisoformat(val)
                else:
                    parsed_date = datetime.strptime(val[:10], "%Y-%m-%d")
            except (ValueError, TypeError):
                errors.append(
                    f"Field '{q['label']}' must be a valid date (YYYY-MM-DD)"
                )
                continue

            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            allow_future = config.get("allow_future", True)
            allow_past = config.get("allow_past", True)
            min_date_str = config.get("min_date")
            max_date_str = config.get("max_date")

            if not allow_future and parsed_date > today:
                errors.append(f"Field '{q['label']}' cannot be in the future")
                continue
            if not allow_past and parsed_date < today:
                errors.append(f"Field '{q['label']}' cannot be in the past")
                continue

            if min_date_str:
                try:
                    min_date = datetime.strptime(min_date_str, "%Y-%m-%d")
                    if parsed_date < min_date:
                        errors.append(
                            f"Field '{q['label']}' cannot be before {min_date_str}"
                        )
                        continue
                except ValueError:
                    pass

            if max_date_str:
                try:
                    max_date = datetime.strptime(max_date_str, "%Y-%m-%d")
                    if parsed_date > max_date:
                        errors.append(
                            f"Field '{q['label']}' cannot be after {max_date_str}"
                        )
                        continue
                except ValueError:
                    pass

            validated[key] = val

        elif qtype == "multiplechoice":
            options = config.get("options", [])
            allow_multiple = config.get("allow_multiple", False)
            min_sel = config.get("min_selections", 0) or 0
            max_sel = config.get("max_selections")

            if allow_multiple:
                # Value should be a list
                vals = value if isinstance(value, list) else [value]
                invalid_opts = [v for v in vals if v not in options]
                if invalid_opts:
                    errors.append(
                        f"Field '{q['label']}': invalid option(s): {', '.join(str(o) for o in invalid_opts)}"
                    )
                    continue
                if len(vals) < min_sel:
                    errors.append(
                        f"Field '{q['label']}' requires at least {min_sel} selection(s)"
                    )
                    continue
                if max_sel is not None and len(vals) > max_sel:
                    errors.append(
                        f"Field '{q['label']}' allows at most {max_sel} selection(s)"
                    )
                    continue
                validated[key] = vals
            else:
                if value not in options:
                    errors.append(
                        f"Field '{q['label']}': '{value}' is not a valid option"
                    )
                    continue
                validated[key] = value

        else:
            validated[key] = value

    if errors:
        raise ValueError("; ".join(errors))

    # Include any extra data keys not in questions (passthrough)
    for k, v in data.items():
        if k not in validated:
            validated[k] = v

    return validated
