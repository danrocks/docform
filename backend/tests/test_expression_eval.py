"""Tests for expression_eval (Python expression parser/evaluator)."""

import pytest

from expression_eval import (
    evaluate_expression,
    validate_expression_syntax,
)


# ---------------------------------------------------------------------------
# Basic arithmetic
# ---------------------------------------------------------------------------

def test_arithmetic_addition():
    assert evaluate_expression("1 + 2", {}) == 3.0


def test_arithmetic_subtraction():
    assert evaluate_expression("10 - 4", {}) == 6.0


def test_arithmetic_multiplication():
    assert evaluate_expression("3 * 4", {}) == 12.0


def test_arithmetic_division():
    assert evaluate_expression("10 / 4", {}) == 2.5


def test_arithmetic_division_truncated():
    # 10 / 3 = 3.333...
    result = evaluate_expression("10 / 3", {})
    assert result is not None
    assert abs(result - (10 / 3)) < 1e-9


def test_operator_precedence():
    assert evaluate_expression("2 + 3 * 4", {}) == 14.0
    assert evaluate_expression("(2 + 3) * 4", {}) == 20.0
    assert evaluate_expression("20 / 4 / 5", {}) == 1.0


def test_unary_negation():
    assert evaluate_expression("-5", {}) == -5.0
    assert evaluate_expression("-(2 + 3)", {}) == -5.0
    assert evaluate_expression("10 + -3", {}) == 7.0


def test_decimal_literals():
    assert evaluate_expression("0.2", {}) == 0.2
    assert evaluate_expression(".5 + .5", {}) == 1.0
    assert evaluate_expression("100 * 0.2", {}) == 20.0


# ---------------------------------------------------------------------------
# Field references
# ---------------------------------------------------------------------------

def test_field_reference_resolves_value():
    assert evaluate_expression("price", {"price": 42}) == 42.0


def test_field_reference_missing_is_zero():
    assert evaluate_expression("price", {}) == 0.0


def test_field_reference_string_numeric_coerced():
    assert evaluate_expression("price * 2", {"price": "10.5"}) == 21.0


def test_field_reference_non_numeric_treated_as_zero():
    assert evaluate_expression("price + 5", {"price": "abc"}) == 5.0


def test_cross_field_addition():
    data = {"subtotal": 100, "vat_amount": 20}
    assert evaluate_expression("subtotal + vat_amount", data) == 120.0


# ---------------------------------------------------------------------------
# Repeat group references + aggregates
# ---------------------------------------------------------------------------

def test_sum_repeat_group_field():
    data = {"items": [{"price": 10}, {"price": 20}]}
    assert evaluate_expression("sum(items.price)", data) == 30.0


def test_count_repeat_group_field():
    data = {"items": [{"price": 10}, {"price": 20}, {"price": 30}]}
    assert evaluate_expression("count(items.price)", data) == 3.0


def test_count_repeat_group_alone():
    data = {"items": [{"price": 10}, {"price": 20}, {"price": 30}]}
    assert evaluate_expression("count(items)", data) == 3.0


def test_avg_repeat_group_field():
    data = {"items": [{"score": 10}, {"score": 20}, {"score": 30}]}
    assert evaluate_expression("avg(items.score)", data) == 20.0


def test_min_repeat_group_field():
    data = {"items": [{"v": 7}, {"v": 3}, {"v": 9}]}
    assert evaluate_expression("min(items.v)", data) == 3.0


def test_max_repeat_group_field():
    data = {"items": [{"v": 7}, {"v": 3}, {"v": 9}]}
    assert evaluate_expression("max(items.v)", data) == 9.0


# ---------------------------------------------------------------------------
# Element-wise arithmetic
# ---------------------------------------------------------------------------

def test_element_wise_multiplication():
    data = {
        "items": [
            {"quantity": 2, "unit_price": 5},
            {"quantity": 3, "unit_price": 4},
        ]
    }
    # (2*5) + (3*4) = 22
    assert evaluate_expression("sum(items.quantity * items.unit_price)", data) == 22.0


def test_element_wise_with_scalar():
    data = {"items": [{"price": 10}, {"price": 20}]}
    # sum(items.price * 2) = 60
    assert evaluate_expression("sum(items.price * 2)", data) == 60.0


def test_element_wise_subtraction():
    data = {
        "items": [
            {"gross": 100, "discount": 10},
            {"gross": 50, "discount": 5},
        ]
    }
    assert evaluate_expression("sum(items.gross - items.discount)", data) == 135.0


# ---------------------------------------------------------------------------
# Nested expressions
# ---------------------------------------------------------------------------

def test_nested_expression_with_outer_arithmetic():
    data = {"items": [{"subtotal": 100}, {"subtotal": 50}]}
    # sum(items.subtotal) * 0.2 = 30
    assert evaluate_expression("sum(items.subtotal) * 0.2", data) == 30.0


def test_combined_field_and_aggregate():
    data = {
        "subtotal": 100,
        "items": [{"price": 10}, {"price": 20}],
    }
    assert evaluate_expression("subtotal + sum(items.price)", data) == 130.0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_array_aggregates_return_zero():
    data = {"items": []}
    assert evaluate_expression("sum(items.price)", data) == 0.0
    assert evaluate_expression("avg(items.price)", data) == 0.0
    assert evaluate_expression("min(items.price)", data) == 0.0
    assert evaluate_expression("max(items.price)", data) == 0.0
    assert evaluate_expression("count(items.price)", data) == 0.0


def test_missing_repeat_group_returns_zero():
    assert evaluate_expression("sum(items.price)", {}) == 0.0
    assert evaluate_expression("count(items)", {}) == 0.0


def test_division_by_zero():
    assert evaluate_expression("10 / 0", {}) == 0.0
    assert evaluate_expression("10 / x", {}) == 0.0
    assert evaluate_expression("10 / x", {"x": 0}) == 0.0


def test_missing_nested_field_treated_as_zero():
    data = {"items": [{"price": 10}, {}, {"price": 20}]}
    assert evaluate_expression("sum(items.price)", data) == 30.0


def test_invalid_expression_returns_none():
    assert evaluate_expression("1 +", {}) is None
    assert evaluate_expression("(", {}) is None
    assert evaluate_expression("foo(bar)", {}) is None  # unknown function


def test_empty_or_non_string_expression_returns_none():
    assert evaluate_expression("", {}) is None
    assert evaluate_expression("   ", {}) is None


def test_data_not_dict_treated_as_empty():
    assert evaluate_expression("price", None) == 0.0  # type: ignore[arg-type]


def test_array_top_level_collapses_to_sum():
    data = {"items": [{"price": 10}, {"price": 20}]}
    # No aggregate wrapper: collapse to sum so we still return a number
    assert evaluate_expression("items.price", data) == 30.0


def test_negation_of_array():
    data = {"items": [{"v": 1}, {"v": 2}]}
    # -items.v -> [-1, -2], collapsed to sum -> -3
    assert evaluate_expression("-items.v", data) == -3.0


# ---------------------------------------------------------------------------
# Syntax validation
# ---------------------------------------------------------------------------

def test_validate_expression_syntax_valid():
    errors = validate_expression_syntax(
        "sum(items.price) + tax", {"items", "tax", "price"}
    )
    assert errors == []


def test_validate_expression_syntax_unknown_field():
    errors = validate_expression_syntax(
        "sum(unknown_field.price)", {"items"}
    )
    assert len(errors) == 1
    assert "unknown_field" in errors[0]


def test_validate_expression_syntax_parse_error():
    errors = validate_expression_syntax("1 +", {"items"})
    assert len(errors) >= 1


def test_validate_expression_syntax_unknown_function():
    errors = validate_expression_syntax("foo(bar)", {"bar"})
    assert len(errors) >= 1


def test_validate_expression_syntax_empty():
    errors = validate_expression_syntax("", {"items"})
    assert len(errors) >= 1


# ---------------------------------------------------------------------------
# Realistic end-to-end-ish scenarios
# ---------------------------------------------------------------------------

def test_invoice_total_scenario():
    data = {
        "line_items": [
            {"quantity": 2, "unit_price": 50},
            {"quantity": 1, "unit_price": 25},
        ],
    }
    subtotal = evaluate_expression(
        "sum(line_items.quantity * line_items.unit_price)", data
    )
    assert subtotal == 125.0


def test_total_with_vat_scenario():
    data = {
        "line_items": [
            {"quantity": 2, "unit_price": 50},
            {"quantity": 1, "unit_price": 25},
        ],
    }
    expr = (
        "sum(line_items.quantity * line_items.unit_price) "
        "+ sum(line_items.quantity * line_items.unit_price) * 0.2"
    )
    assert evaluate_expression(expr, data) == 150.0


@pytest.mark.parametrize(
    "expr,data,expected",
    [
        ("1 + 2 + 3", {}, 6.0),
        ("2 * 3 + 4", {}, 10.0),
        ("2 * (3 + 4)", {}, 14.0),
        ("100 - 50 - 25", {}, 25.0),
        ("100 - (50 - 25)", {}, 75.0),
        ("price + tax", {"price": 100, "tax": 20}, 120.0),
    ],
)
def test_parametrized_arithmetic(expr, data, expected):
    assert evaluate_expression(expr, data) == expected


# ---------------------------------------------------------------------------
# Integration with question_schema (validate_submission_data + recompute)
# ---------------------------------------------------------------------------

from question_schema import validate_questions, validate_submission_data  # noqa: E402


def test_submission_recomputes_total_from_repeat_group():
    components = [
        {
            "type": "repeat", "id": "items", "label": "Line Items",
            "components": [
                {"type": "number", "id": "qty", "label": "Qty"},
                {"type": "number", "id": "unit_price", "label": "Unit Price"},
            ],
        },
        {
            "type": "number", "id": "total", "label": "Total",
            "expression": "sum(items.qty * items.unit_price)",
            "decimalPlaces": 2,
        },
    ]
    data = {
        "items": [{"qty": 2, "unit_price": 50}, {"qty": 1, "unit_price": 25}],
        "total": 999,  # client-submitted value (should be overwritten)
    }
    result = validate_submission_data(components, data)
    assert result["total"] == 125.0


def test_submission_chained_expressions():
    components = [
        {"type": "number", "id": "subtotal", "label": "Subtotal"},
        {"type": "number", "id": "vat", "label": "VAT",
         "expression": "subtotal * 0.2", "decimalPlaces": 2},
        {"type": "number", "id": "total", "label": "Total",
         "expression": "subtotal + vat", "decimalPlaces": 2},
    ]
    result = validate_submission_data(components, {"subtotal": 100})
    assert result["vat"] == 20.0
    assert result["total"] == 120.0


def test_submission_skips_validation_for_computed_field():
    # Computed field with required:true would normally fail because no value
    # is submitted. The skip should let it through and recompute correctly.
    components = [
        {"type": "number", "id": "a", "label": "A"},
        {"type": "number", "id": "b", "label": "B"},
        {
            "type": "number", "id": "total", "label": "Total",
            "expression": "a + b",
            "required": True,
            "decimalPlaces": 2,
        },
    ]
    result = validate_submission_data(components, {"a": 10, "b": 5})
    assert result["total"] == 15.0


def test_submission_ignores_floating_point_decimal_places_on_computed():
    # 7 * 0.1 = 0.7000000000000001 in IEEE-754. Without skipping number
    # validation for computed fields the decimalPlaces check would reject
    # the recomputed value. With the skip the field round-trips cleanly.
    components = [
        {"type": "number", "id": "a", "label": "A"},
        {
            "type": "number", "id": "tenths", "label": "Tenths",
            "expression": "a * 0.1",
            "decimalPlaces": 2,
        },
    ]
    result = validate_submission_data(components, {"a": 7})
    assert result["tenths"] == 0.7


def test_submission_ignores_min_max_on_computed():
    # min/max on a computed field should not block submission if the inputs
    # produce an out-of-range value — the field is derived.
    components = [
        {"type": "number", "id": "a", "label": "A"},
        {
            "type": "number", "id": "doubled", "label": "Doubled",
            "expression": "a * 2",
            "max": 5,  # would normally reject 20 but it's a computed field
        },
    ]
    result = validate_submission_data(components, {"a": 10})
    assert result["doubled"] == 20.0


def test_recompute_skips_repeat_children():
    # An `expression` on a number field inside a repeat group should NOT be
    # collected at the top level (the references inside the expression don't
    # mean the same thing per-row vs. globally). The repeat-child computed
    # field is left untouched by `_recompute_expressions`.
    components = [
        {
            "type": "repeat", "id": "items", "label": "Items",
            "components": [
                {"type": "number", "id": "qty", "label": "Qty"},
                {"type": "number", "id": "unit_price", "label": "Unit Price"},
                # This per-row computed field is NOT supported and must be
                # ignored by the top-level recompute step.
                {
                    "type": "number", "id": "row_total", "label": "Row total",
                    "expression": "qty * unit_price",
                },
            ],
        },
    ]
    result = validate_submission_data(
        components,
        {"items": [{"qty": 2, "unit_price": 50, "row_total": 100}]},
    )
    # No phantom top-level "row_total" was written.
    assert "row_total" not in result
    # The submitted per-row value is preserved verbatim.
    assert result["items"][0]["row_total"] == 100


def test_validate_questions_rejects_invalid_expression_field():
    components = [
        {"type": "number", "id": "total", "label": "Total",
         "expression": "sum(unknown.x)"},
    ]
    with pytest.raises(ValueError, match="Unknown field reference"):
        validate_questions(components)


def test_validate_questions_rejects_parse_error():
    components = [
        {"type": "number", "id": "total", "label": "Total", "expression": "1 +"},
    ]
    with pytest.raises(ValueError, match="invalid expression"):
        validate_questions(components)


def test_validate_questions_accepts_valid_expression():
    components = [
        {"type": "repeat", "id": "items", "label": "Line Items",
         "components": [{"type": "number", "id": "price", "label": "Price"}]},
        {"type": "number", "id": "total", "label": "Total",
         "expression": "sum(items.price)", "decimalPlaces": 2},
    ]
    # Should not raise.
    validate_questions(components)


def test_validate_questions_rejects_expression_inside_repeat():
    # Expressions on number fields inside a repeat group are unsupported and
    # must be rejected at schema-validation time so authors get a clear error
    # rather than silently-broken or unvalidated submissions.
    components = [
        {
            "type": "repeat", "id": "items", "label": "Items",
            "components": [
                {"type": "number", "id": "qty", "label": "Qty"},
                {"type": "number", "id": "unit_price", "label": "Unit Price"},
                {"type": "number", "id": "row_total", "label": "Row total",
                 "expression": "qty * unit_price"},
            ],
        },
    ]
    with pytest.raises(
        ValueError, match="not supported on number components inside a repeat group"
    ):
        validate_questions(components)


def test_validate_questions_rejects_expression_inside_nested_repeat_via_dialog():
    # Dialogs are transparent containers, but if a dialog is *inside* a repeat
    # any expression on a number child should still be rejected.
    components = [
        {
            "type": "repeat", "id": "groups", "label": "Groups",
            "components": [
                {
                    "type": "dialog", "id": "row_dialog", "title": "Row",
                    "components": [
                        {"type": "number", "id": "x", "label": "X"},
                        {"type": "number", "id": "doubled", "label": "Doubled",
                         "expression": "x * 2"},
                    ],
                },
            ],
        },
    ]
    with pytest.raises(
        ValueError, match="not supported on number components inside a repeat group"
    ):
        validate_questions(components)


def test_validate_questions_allows_expression_inside_top_level_dialog():
    components = [
        {"type": "number", "id": "a", "label": "A"},
        {
            "type": "dialog", "id": "totals", "title": "Totals",
            "components": [
                {"type": "number", "id": "doubled", "label": "Doubled",
                 "expression": "a * 2"},
            ],
        },
    ]
    # Should not raise — dialog at top level is transparent.
    validate_questions(components)


def test_client_value_for_computed_field_does_not_leak_into_recompute():
    # When a computed field is defined out-of-order (it references a sibling
    # computed field that appears later in document order), the recompute step
    # cannot produce the right value — that's the schema author's
    # responsibility. But the malicious client value MUST NOT leak in via the
    # catch-all copy. Without the leak fix, `total` would evaluate
    # `subtotal + vat` as `100 + 999 = 1099` (using the client `vat=999`).
    # With the leak fix, `vat` is treated as missing (0) → `total = 100`.
    components = [
        {"type": "number", "id": "total", "label": "Total",
         "expression": "subtotal + vat", "decimalPlaces": 2},
        {"type": "number", "id": "vat", "label": "VAT",
         "expression": "subtotal * 0.2", "decimalPlaces": 2},
        {"type": "number", "id": "subtotal", "label": "Subtotal"},
    ]
    result = validate_submission_data(
        components,
        {"subtotal": 100, "vat": 999, "total": 0},
    )
    # 1099 would indicate the leak is still present. 100 means the leak is
    # closed (regardless of the fact that the schema is also poorly ordered).
    assert result["total"] == 100
    assert result["vat"] == 20.0
    assert result["subtotal"] == 100


def test_client_value_dropped_when_expression_eval_returns_none():
    # If `evaluate_expression` returns None (e.g. a malformed expression that
    # somehow slipped past `validate_questions`) the recompute step skips
    # the field. The client-submitted value for that field must NOT be
    # preserved verbatim via the catch-all copy.
    components = [
        # The expression here is syntactically invalid, but it doesn't go
        # through `validate_questions` so `validate_submission_data` is the
        # only line of defense.
        {"type": "number", "id": "broken", "label": "Broken",
         "expression": "1 +"},
    ]
    result = validate_submission_data(components, {"broken": 99999})
    # The malicious client value must not leak through.
    assert result.get("broken") != 99999


def test_repeat_child_with_non_numeric_value_is_rejected_post_fix():
    # Even if a malicious schema somehow reached `validate_submission_data`
    # with `expression` on a repeat-child number field, the defense-in-depth
    # `inside_repeat` flag in `_validate_component` falls back to normal
    # number validation and rejects non-numeric input.
    from question_schema import _validate_component
    comp = {
        "type": "number", "id": "row_total", "label": "Row total",
        "expression": "qty * unit_price",
    }
    errors: list = []
    validated: dict = {}
    _validate_component(
        comp, {"row_total": "not-a-number"}, validated, errors, inside_repeat=True
    )
    assert errors  # rejected
    assert "row_total" not in validated
