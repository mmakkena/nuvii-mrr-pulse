"""
Tests for condition evaluator with JsonLogic.
Demonstrates support for nested fields and complex conditions.
"""
import pytest
from app.services.condition_evaluator import (
    evaluate_conditions,
    extract_event_data,
    build_amount_threshold_rule,
    build_nested_field_rule,
    build_metadata_rule,
)


def test_simple_amount_condition():
    """Test simple amount > threshold condition."""
    event_data = {"amount": 1500, "currency": "usd"}
    condition = {">": [{"var": "amount"}, 1000]}

    assert evaluate_conditions(event_data, condition) is True

    event_data_below = {"amount": 500, "currency": "usd"}
    assert evaluate_conditions(event_data_below, condition) is False


def test_nested_field_access():
    """Test nested field access with dot notation."""
    event_data = {
        "amount": 5000,
        "card": {
            "brand": "visa",
            "country": "US",
            "funding": "credit"
        }
    }

    # Test card.brand == "visa"
    condition = {"==": [{"var": "card.brand"}, "visa"]}
    assert evaluate_conditions(event_data, condition) is True

    # Test card.country == "US"
    condition = {"==": [{"var": "card.country"}, "US"]}
    assert evaluate_conditions(event_data, condition) is True

    # Test card.funding == "debit" (should fail)
    condition = {"==": [{"var": "card.funding"}, "debit"]}
    assert evaluate_conditions(event_data, condition) is False


def test_metadata_access():
    """Test accessing Stripe metadata fields."""
    event_data = {
        "amount": 1000,
        "metadata": {
            "customer_tier": "premium",
            "subscription_type": "annual",
            "internal_id": "12345"
        }
    }

    # Test metadata.customer_tier == "premium"
    condition = {"==": [{"var": "metadata.customer_tier"}, "premium"]}
    assert evaluate_conditions(event_data, condition) is True

    # Test metadata.subscription_type == "monthly" (should fail)
    condition = {"==": [{"var": "metadata.subscription_type"}, "monthly"]}
    assert evaluate_conditions(event_data, condition) is False


def test_complex_nested_and_condition():
    """Test complex AND condition with nested fields."""
    event_data = {
        "amount": 12000,
        "currency": "usd",
        "card": {
            "brand": "visa",
            "country": "US"
        },
        "metadata": {
            "customer_tier": "premium"
        }
    }

    # (amount > $100 AND card.brand == "visa" AND metadata.customer_tier == "premium")
    condition = {
        "and": [
            {">": [{"var": "amount"}, 10000]},
            {"==": [{"var": "card.brand"}, "visa"]},
            {"==": [{"var": "metadata.customer_tier"}, "premium"]}
        ]
    }

    assert evaluate_conditions(event_data, condition) is True


def test_complex_or_condition():
    """Test complex OR condition with nested fields."""
    event_data = {
        "amount": 7500,
        "currency": "usd",
        "card": {
            "brand": "amex",
            "country": "US"
        }
    }

    # (amount > $100 AND currency == "usd") OR (card.brand == "amex" AND amount > $50)
    condition = {
        "or": [
            {
                "and": [
                    {">": [{"var": "amount"}, 10000]},
                    {"==": [{"var": "currency"}, "usd"]}
                ]
            },
            {
                "and": [
                    {"==": [{"var": "card.brand"}, "amex"]},
                    {">": [{"var": "amount"}, 5000]}
                ]
            }
        ]
    }

    # Should pass because second OR branch is true
    assert evaluate_conditions(event_data, condition) is True


def test_missing_nested_field():
    """Test that missing nested fields are handled gracefully."""
    event_data = {
        "amount": 1000,
        "currency": "usd"
        # card field is missing
    }

    # Test card.brand == "visa" (card doesn't exist)
    condition = {"==": [{"var": "card.brand"}, "visa"]}
    # Should return False (or handle gracefully)
    result = evaluate_conditions(event_data, condition)
    assert result is False


def test_deep_nested_access():
    """Test deeply nested field access."""
    event_data = {
        "billing": {
            "address": {
                "country": "US",
                "state": "CA",
                "postal_code": "94102"
            }
        }
    }

    # Test billing.address.country == "US"
    condition = {"==": [{"var": "billing.address.country"}, "US"]}
    assert evaluate_conditions(event_data, condition) is True

    # Test billing.address.state == "NY" (should fail)
    condition = {"==": [{"var": "billing.address.state"}, "NY"]}
    assert evaluate_conditions(event_data, condition) is False


def test_helper_functions():
    """Test helper functions for building rules."""
    # Test build_amount_threshold_rule
    rule = build_amount_threshold_rule(1000, "usd")
    assert rule == {
        "and": [
            {">": [{"var": "amount"}, 1000]},
            {"==": [{"var": "currency"}, "usd"]}
        ]
    }

    # Test build_nested_field_rule
    rule = build_nested_field_rule("card.brand", "==", "visa")
    assert rule == {"==": [{"var": "card.brand"}, "visa"]}

    # Test build_metadata_rule
    rule = build_metadata_rule("customer_tier", "premium")
    assert rule == {"==": [{"var": "metadata.customer_tier"}, "premium"]}


def test_no_conditions_allows_all():
    """Test that no conditions means allow all events."""
    event_data = {"amount": 1, "currency": "usd"}

    # Empty condition
    assert evaluate_conditions(event_data, {}) is True

    # None condition
    assert evaluate_conditions(event_data, None) is True


def test_real_world_payment_failure_scenario():
    """Test real-world scenario: Alert only for payment failures > $10 USD."""
    # Payment failure of $12 USD - should trigger
    event_data_12usd = {
        "amount": 1200,  # cents
        "currency": "usd",
        "failure_code": "card_declined",
        "status": "failed"
    }

    # Payment failure of $5 USD - should NOT trigger
    event_data_5usd = {
        "amount": 500,  # cents
        "currency": "usd",
        "failure_code": "card_declined",
        "status": "failed"
    }

    # Rule: amount > $10 (1000 cents) AND currency == "usd"
    condition = {
        "and": [
            {">": [{"var": "amount"}, 1000]},
            {"==": [{"var": "currency"}, "usd"]}
        ]
    }

    assert evaluate_conditions(event_data_12usd, condition) is True
    assert evaluate_conditions(event_data_5usd, condition) is False


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
