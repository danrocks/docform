"""Tests for the expression evaluator."""

import pytest
from expression_eval import (
    evaluate_expression,
    evaluate_computed_fields,
    parse_expression,
    ExpressionError,
)


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------

class TestArithmetic:
    def test_addition(self):
        assert evaluate_expression("2 + 3", {}) == 5.0

    def test_subtraction(self):
        assert evaluate_expression("10 - 4", {}) == 6.0

    def test_multiplication(self):
        assert evaluate_expression("3 * 7", {}) == 21.0

    def test_division(self):
        assert evaluate_expression("20 / 4", {}) == 5.0

    def test_division_by_zero(self):
        assert evaluate_expression("10 / 0", {}) == 0.0

    def test_operator_precedence(self):
        assert evaluate_expression("2 + 3 * 4", {}) == 14.0

    def test_parentheses(self):
        assert evaluate_expression("(2 + 3) * 4", {}) == 20.0

    def test_negative(self):
        assert evaluate_expression("-5 + 3", {}) == -2.0

    def test_decimal(self):
        assert evaluate_expression("3.14 * 2", {}) == pytest.approx(6.28)

    def test_nested_parens(self):
        assert evaluate_expression("((1 + 2) * (3 + 4))", {}) == 21.0


# ---------------------------------------------------------------------------
# Field references
# ---------------------------------------------------------------------------

class TestFieldRefs:
    def test_simple_ref(self):
        assert evaluate_expression("price", {"price": 42}) == 42.0

    def test_ref_arithmetic(self):
        assert evaluate_expression("price * 1.2", {"price": 100}) == 120.0

    def test_missing_field_defaults_zero(self):
        assert evaluate_expression("missing_field", {}) == 0.0

    def test_empty_string_defaults_zero(self):
        assert evaluate_expression("field", {"field": ""}) == 0.0

    def test_string_number(self):
        assert evaluate_expression("field", {"field": "42.5"}) == 42.5

    def test_multiple_refs(self):
        assert evaluate_expression("a + b * c", {"a": 1, "b": 2, "c": 3}) == 7.0


# ---------------------------------------------------------------------------
# Aggregate functions
# ---------------------------------------------------------------------------

class TestAggregates:
    @pytest.fixture()
    def invoice_data(self):
        return {
            "items": [
                {"quantity": 2, "unit_price": 50},
                {"quantity": 1, "unit_price": 100},
                {"quantity": 3, "unit_price": 25},
            ]
        }

    def test_sum_simple(self, invoice_data):
        assert evaluate_expression("sum(items.unit_price)", invoice_data) == 175.0

    def test_sum_product(self, invoice_data):
        result = evaluate_expression(
            "sum(items.quantity * items.unit_price)", invoice_data
        )
        assert result == 275.0  # 2*50 + 1*100 + 3*25

    def test_count(self, invoice_data):
        assert evaluate_expression("count(items)", invoice_data) == 3.0

    def test_avg(self, invoice_data):
        assert evaluate_expression("avg(items.unit_price)", invoice_data) == pytest.approx(
            175.0 / 3
        )

    def test_min(self, invoice_data):
        assert evaluate_expression("min(items.unit_price)", invoice_data) == 25.0

    def test_max(self, invoice_data):
        assert evaluate_expression("max(items.unit_price)", invoice_data) == 100.0

    def test_empty_group(self):
        assert evaluate_expression("sum(items.price)", {"items": []}) == 0.0

    def test_missing_group(self):
        assert evaluate_expression("sum(items.price)", {}) == 0.0

    def test_sum_with_arithmetic(self, invoice_data):
        # sum + constant
        result = evaluate_expression(
            "sum(items.quantity * items.unit_price) + 20", invoice_data
        )
        assert result == 295.0


# ---------------------------------------------------------------------------
# round()
# ---------------------------------------------------------------------------

class TestRound:
    def test_round_basic(self):
        assert evaluate_expression("round(10 / 3, 2)", {}) == 3.33

    def test_round_zero_places(self):
        assert evaluate_expression("round(10.7, 0)", {}) == 11.0

    def test_round_field(self):
        assert evaluate_expression("round(price * 0.2, 2)", {"price": 33.33}) == pytest.approx(6.67)


# ---------------------------------------------------------------------------
# evaluate_computed_fields
# ---------------------------------------------------------------------------

class TestComputedFields:
    def test_top_level_expression(self):
        components = [
            {"type": "number", "id": "price", "label": "Price"},
            {"type": "number", "id": "tax", "label": "Tax", "expression": "price * 0.2"},
        ]
        data = {"price": 100}
        result = evaluate_computed_fields(components, data)
        assert result["tax"] == 20.0
        assert result["price"] == 100  # original preserved

    def test_repeat_group_total(self):
        components = [
            {
                "type": "repeat",
                "id": "items",
                "label": "Items",
                "components": [
                    {"type": "number", "id": "qty", "label": "Qty"},
                    {"type": "number", "id": "price", "label": "Price"},
                ],
            },
            {
                "type": "number",
                "id": "total",
                "label": "Total",
                "expression": "sum(items.qty * items.price)",
            },
        ]
        data = {
            "items": [
                {"qty": 2, "price": 10},
                {"qty": 5, "price": 3},
            ]
        }
        result = evaluate_computed_fields(components, data)
        assert result["total"] == 35.0  # 2*10 + 5*3

    def test_chained_expressions(self):
        components = [
            {"type": "number", "id": "base", "label": "Base"},
            {"type": "number", "id": "tax", "label": "Tax", "expression": "base * 0.2"},
            {"type": "number", "id": "total", "label": "Total", "expression": "base + tax"},
        ]
        data = {"base": 100}
        result = evaluate_computed_fields(components, data)
        assert result["tax"] == 20.0
        assert result["total"] == 120.0

    def test_original_data_not_mutated(self):
        components = [
            {"type": "number", "id": "x", "label": "X", "expression": "42"},
        ]
        data = {"other": "value"}
        result = evaluate_computed_fields(components, data)
        assert "x" not in data  # original unchanged
        assert result["x"] == 42.0

    def test_expression_inside_repeat_row(self):
        components = [
            {
                "type": "repeat",
                "id": "rows",
                "label": "Rows",
                "components": [
                    {"type": "number", "id": "qty", "label": "Qty"},
                    {"type": "number", "id": "price", "label": "Price"},
                    {
                        "type": "number",
                        "id": "line_total",
                        "label": "Line total",
                        "expression": "qty * price",
                    },
                ],
            },
        ]
        data = {
            "rows": [
                {"qty": 3, "price": 10},
                {"qty": 2, "price": 25},
            ]
        }
        result = evaluate_computed_fields(components, data)
        assert result["rows"][0]["line_total"] == 30.0
        assert result["rows"][1]["line_total"] == 50.0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrors:
    def test_empty_expression(self):
        with pytest.raises(ExpressionError):
            parse_expression("")

    def test_unknown_function(self):
        with pytest.raises(ExpressionError, match="Unknown function"):
            parse_expression("foo(x)")

    def test_dotted_ref_outside_aggregate(self):
        with pytest.raises(ExpressionError, match="only be used inside"):
            evaluate_expression("items.price", {"items": [{"price": 10}]})

    def test_trailing_token(self):
        with pytest.raises(ExpressionError, match="Unexpected token"):
            parse_expression("1 + 2 3")
