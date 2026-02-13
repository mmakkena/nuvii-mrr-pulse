"""
Condition Evaluation Engine for Alert Rules using JsonLogic

Uses json-logic for flexible, industry-standard rule evaluation.
JsonLogic supports complex nested conditions with AND/OR logic and nested field access.

Example JsonLogic rules:

1. Simple: amount > $10
   {">" : [{"var": "amount"}, 1000]}

2. AND logic: amount > $10 AND currency == "usd"
   {"and": [
     {">": [{"var": "amount"}, 1000]},
     {"==": [{"var": "currency"}, "usd"]}
   ]}

3. Nested field access: metadata.customer_tier == "premium"
   {"==": [{"var": "metadata.customer_tier"}, "premium"]}

4. Complex nested: card brand is "visa" AND card country is "US"
   {"and": [
     {"==": [{"var": "card.brand"}, "visa"]},
     {"==": [{"var": "card.country"}, "US"]}
   ]}

5. Multiple conditions with nesting:
   (amount > $100 AND currency == "usd") OR (card.brand == "amex" AND amount > $50)
   {"or": [
     {"and": [
       {">": [{"var": "amount"}, 10000]},
       {"==": [{"var": "currency"}, "usd"]}
     ]},
     {"and": [
       {"==": [{"var": "card.brand"}, "amex"]},
       {">": [{"var": "amount"}, 5000]}
     ]}
   ]}

Supported operators:
- Comparison: ==, !=, ===, !==, >, >=, <, <=
- Logic: and, or, !, !!
- Strings: in (substring), cat (concat)
- Arrays: in (contains), map, filter, reduce, all, none, some
- Math: +, -, *, /, %, min, max
- Other: if, missing, missing_some

Nested field access:
- Use dot notation: {"var": "parent.child.grandchild"}
- Works with any depth: {"var": "a.b.c.d.e"}
- Returns null/undefined if path doesn't exist

Docs: https://github.com/nadirizr/json-logic-py
"""
import logging
from typing import Any, Dict, Optional
from json_logic import jsonLogic

logger = logging.getLogger(__name__)


def evaluate_conditions(
    event_data: Dict[str, Any],
    conditions_config: Optional[Dict[str, Any]]
) -> bool:
    """
    Evaluate JsonLogic conditions against event data.

    Args:
        event_data: Dictionary containing event fields (supports nested fields)
        conditions_config: JsonLogic rule

            Example with nested fields:
            {
                "and": [
                    {">": [{"var": "amount"}, 1000]},
                    {"==": [{"var": "card.brand"}, "visa"]},
                    {"==": [{"var": "metadata.customer_tier"}, "premium"]}
                ]
            }

    Returns:
        True if conditions pass, False otherwise
    """
    try:
        # If no conditions configured, always pass (allow all)
        if not conditions_config:
            logger.debug("No conditions configured, allowing event")
            return True

        # Evaluate using JsonLogic (supports nested field access with dot notation)
        result = jsonLogic(conditions_config, event_data)

        logger.debug(
            f"Evaluated conditions: {conditions_config} | "
            f"Data fields: {list(event_data.keys())} | Result: {result}"
        )

        # JsonLogic returns truthy/falsy values, convert to boolean
        return bool(result)

    except Exception as e:
        logger.error(
            f"Error evaluating conditions: {e} | "
            f"Config: {conditions_config} | Data keys: {list(event_data.keys())}",
            exc_info=True
        )
        # On error, default to NOT creating alert (fail closed)
        return False


def extract_event_data(stripe_event: Dict[str, Any], event_type: str) -> Dict[str, Any]:
    """
    Extract relevant fields from Stripe event for condition evaluation.
    Returns nested structure to support dot notation access in JsonLogic.

    Args:
        stripe_event: Raw Stripe event object
        event_type: Type of event (e.g., "charge.failed", "charge.dispute.created")

    Returns:
        Dictionary of fields (including nested objects) for condition evaluation
    """
    data = stripe_event.get("data", {})
    obj = data.get("object", {})

    # Common fields
    event_data = {
        "event_type": event_type,
        "id": obj.get("id"),
        "object": obj.get("object"),
    }

    # Payment/Charge fields
    if obj.get("object") in ["charge", "payment_intent"]:
        payment_method_details = obj.get("payment_method_details", {})
        billing_details = obj.get("billing_details", {})

        # Flatten AND preserve nested structure for flexibility
        event_data.update({
            # Flat fields (for simple access)
            "amount": obj.get("amount", 0),  # Amount in cents
            "amount_usd": obj.get("amount", 0) / 100,  # Amount in dollars
            "currency": obj.get("currency", "").lower(),
            "status": obj.get("status"),
            "failure_code": obj.get("failure_code"),
            "failure_message": obj.get("failure_message"),
            "customer": obj.get("customer"),
            "customer_email": billing_details.get("email") if billing_details else None,
            "description": obj.get("description"),

            # Nested structures (for advanced access)
            "card": {
                "brand": payment_method_details.get("card", {}).get("brand") if payment_method_details else None,
                "country": payment_method_details.get("card", {}).get("country") if payment_method_details else None,
                "funding": payment_method_details.get("card", {}).get("funding") if payment_method_details else None,
                "last4": payment_method_details.get("card", {}).get("last4") if payment_method_details else None,
            },
            "billing": {
                "email": billing_details.get("email") if billing_details else None,
                "name": billing_details.get("name") if billing_details else None,
                "phone": billing_details.get("phone") if billing_details else None,
                "address": billing_details.get("address") if billing_details else {},
            },
            "metadata": obj.get("metadata", {}),  # Custom metadata from Stripe
        })

    # Dispute fields
    if obj.get("object") == "dispute":
        charge = obj.get("charge", {})
        event_data.update({
            "amount": obj.get("amount", 0),
            "amount_usd": obj.get("amount", 0) / 100,
            "currency": obj.get("currency", "").lower(),
            "reason": obj.get("reason"),
            "status": obj.get("status"),
            "customer": charge.get("customer") if isinstance(charge, dict) else None,
            "is_charge_refundable": obj.get("is_charge_refundable"),
            "metadata": obj.get("metadata", {}),
        })

    # Refund fields
    if obj.get("object") == "refund":
        event_data.update({
            "amount": obj.get("amount", 0),
            "amount_usd": obj.get("amount", 0) / 100,
            "currency": obj.get("currency", "").lower(),
            "reason": obj.get("reason"),
            "status": obj.get("status"),
            "metadata": obj.get("metadata", {}),
        })

    # Subscription fields
    if obj.get("object") == "subscription":
        items = obj.get("items", {}).get("data", [])
        plan = items[0].get("plan", {}) if items else {}

        event_data.update({
            "status": obj.get("status"),
            "customer": obj.get("customer"),
            "cancel_at_period_end": obj.get("cancel_at_period_end"),
            "current_period_end": obj.get("current_period_end"),
            "plan": {
                "amount": plan.get("amount", 0) if plan else 0,
                "interval": plan.get("interval") if plan else None,
                "currency": plan.get("currency", "").lower() if plan else None,
            },
            "metadata": obj.get("metadata", {}),
        })

    # Payout fields
    if obj.get("object") == "payout":
        event_data.update({
            "amount": obj.get("amount", 0),
            "amount_usd": obj.get("amount", 0) / 100,
            "currency": obj.get("currency", "").lower(),
            "status": obj.get("status"),
            "failure_code": obj.get("failure_code"),
            "failure_message": obj.get("failure_message"),
            "type": obj.get("type"),
            "method": obj.get("method"),
            "metadata": obj.get("metadata", {}),
        })

    return event_data


# Helper functions for building common JsonLogic rules

def build_amount_threshold_rule(min_amount_cents: int, currency: Optional[str] = None) -> Dict[str, Any]:
    """
    Build a simple amount threshold rule.

    Args:
        min_amount_cents: Minimum amount in cents
        currency: Optional currency filter

    Returns:
        JsonLogic rule

    Example:
        rule = build_amount_threshold_rule(1000, "usd")
        # Returns: {"and": [{">": [{"var": "amount"}, 1000]}, {"==": [{"var": "currency"}, "usd"]}]}
    """
    conditions = [{">": [{"var": "amount"}, min_amount_cents]}]

    if currency:
        conditions.append({"==": [{"var": "currency"}, currency.lower()]})

    if len(conditions) == 1:
        return conditions[0]
    return {"and": conditions}


def build_amount_range_rule(
    min_amount_cents: int,
    max_amount_cents: int,
    currency: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build an amount range rule.

    Args:
        min_amount_cents: Minimum amount in cents
        max_amount_cents: Maximum amount in cents
        currency: Optional currency filter

    Returns:
        JsonLogic rule
    """
    conditions = [
        {">=": [{"var": "amount"}, min_amount_cents]},
        {"<=": [{"var": "amount"}, max_amount_cents]}
    ]

    if currency:
        conditions.append({"==": [{"var": "currency"}, currency.lower()]})

    return {"and": conditions}


def build_failure_code_rule(failure_codes: list[str], min_amount_cents: Optional[int] = None) -> Dict[str, Any]:
    """
    Build a rule for specific failure codes.

    Args:
        failure_codes: List of failure codes to match
        min_amount_cents: Optional minimum amount threshold

    Returns:
        JsonLogic rule
    """
    conditions = []

    if len(failure_codes) == 1:
        conditions.append({"==": [{"var": "failure_code"}, failure_codes[0]]})
    else:
        conditions.append({"in": [{"var": "failure_code"}, failure_codes]})

    if min_amount_cents is not None:
        conditions.append({">": [{"var": "amount"}, min_amount_cents]})

    if len(conditions) == 1:
        return conditions[0]
    return {"and": conditions}


def build_nested_field_rule(field_path: str, operator: str, value: Any) -> Dict[str, Any]:
    """
    Build a rule for nested fields using dot notation.

    Args:
        field_path: Dot-notation path (e.g., "card.brand", "metadata.customer_tier")
        operator: Comparison operator (==, !=, >, <, etc.)
        value: Value to compare against

    Returns:
        JsonLogic rule

    Example:
        rule = build_nested_field_rule("card.brand", "==", "visa")
        # Returns: {"==": [{"var": "card.brand"}, "visa"]}
    """
    return {operator: [{"var": field_path}, value]}


def build_metadata_rule(metadata_key: str, value: Any, operator: str = "==") -> Dict[str, Any]:
    """
    Build a rule for Stripe metadata fields.

    Args:
        metadata_key: Metadata key name
        value: Value to compare against
        operator: Comparison operator (default: "==")

    Returns:
        JsonLogic rule

    Example:
        rule = build_metadata_rule("customer_tier", "premium")
        # Returns: {"==": [{"var": "metadata.customer_tier"}, "premium"]}
    """
    return {operator: [{"var": f"metadata.{metadata_key}"}, value]}
