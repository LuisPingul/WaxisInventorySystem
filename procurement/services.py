import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


def generate_po_email(procurement_request):
    """
    Generate PO email body using deterministic template.
    Returns (subject, body)
    """
    ing = procurement_request.ingredient
    supplier = procurement_request.supplier
    # Fallback to legacy text if no FK
    supplier_name = getattr(supplier, "company_name", None) or getattr(ing, "supplier", "") or "Supplier"
    supplier_email = getattr(supplier, "email", "") or "supplier@example.com"
    contact_person = getattr(supplier, "contact_person", "") or "Procurement Contact"
    lead_time = getattr(supplier, "lead_time_days", 3)
    supplier_rating = getattr(supplier, "rating", None)

    qty = procurement_request.requested_quantity
    priority_display = procurement_request.get_priority_display()
    reason = procurement_request.reason or "Restocking - low inventory"
    requested_by = getattr(procurement_request.requested_by, "username", "Waxi's System")

    # Priority-specific language
    priority_phrases = {
        "CRITICAL": "URGENT - Critical stock level",
        "HIGH": "High priority - Stock running low",
        "NORMAL": "Normal priority - Scheduled restock",
        "LOW": "Low priority - Advance planning",
    }
    priority_note = priority_phrases.get(procurement_request.priority, "Restocking")

    subject = f"Purchase Order Request - {ing.name} ({qty} {ing.unit})"

    body = (
        f"Subject: {subject}\n\n"
        f"Dear {contact_person} at {supplier_name},\n\n"
        f"{priority_note}: We would like to place a purchase order for "
        f"{qty} {ing.unit} of {ing.name} ({ing.get_category_display()}).\n\n"
        f"Current Inventory Status:\n"
        f"  - Current Stock: {ing.quantity} {ing.unit}\n"
        f"  - Minimum Threshold: {ing.minimum_stock} {ing.unit}\n"
        f"  - Maximum Capacity: {ing.maximum_stock} {ing.unit}\n\n"
        f"Order Details:\n"
        f"  - Priority: {priority_display}\n"
        f"  - Reason: {reason}\n"
        f"  - Requested by: {requested_by}\n"
        f"  - Expected Lead Time: {lead_time} business days\n"
        f"{f'  - Supplier Rating: {supplier_rating}/5.00' if supplier_rating else ''}\n\n"
        f"Please confirm availability, pricing, and expected delivery date within {lead_time} days "
        f"to Waxi's main kitchen facility.\n\n"
        f"Kindly acknowledge receipt of this order and provide an estimated delivery schedule.\n\n"
        f"Thank you for your prompt attention to this matter.\n\n"
        f"Best regards,\n"
        f"Waxi's Procurement Team\n"
        f"SND Foods International Inc.\n"
        f"Email: procurement@waxis.local\n"
        f"Phone: +63-xxx-xxx-xxxx"
    )

    return subject, body


def generate_executive_summary(context_dict):
    """
    Rule-based Executive Summary for dashboard.
    context_dict: {total, low, critical, pending, distribution}
    """
    total = context_dict.get("total", 0)
    low = context_dict.get("low", 0)
    critical = context_dict.get("critical", 0)
    pending = context_dict.get("pending", 0)
    distribution = context_dict.get("distribution", [])

    # Category breakdown
    cat_parts = []
    for d in distribution:
        cat_name = d.get("category", "")
        cat_count = d.get("count", 0)
        if cat_count > 0:
            cat_parts.append(f"{cat_name}: {cat_count}")
    cat_summary = ", ".join(cat_parts) if cat_parts else "No category data"

    if critical > 0:
        return (
            f"⚠️ IMMEDIATE ACTION REQUIRED: {critical} ingredient(s) CRITICAL/OUT of stock, {low} LOW. "
            f"{pending} procurement request(s) pending. "
            f"Category distribution: {cat_summary}. "
            f"RECOMMENDATION: Approve all HIGH-risk PRs today; contact top 3 suppliers for expedited delivery on critical items."
        )
    elif low > 0:
        return (
            f"📋 MONITORING NEEDED: {low} low-stock items out of {total} total ingredients. "
            f"{pending} procurement request(s) pending. "
            f"Category distribution: {cat_summary}. "
            f"RECOMMENDATION: Review LOW items for reorder prioritization; ensure pending PRs are processed within 48 hours."
        )
    else:
        return (
            f"✅ INVENTORY HEALTHY: {total} ingredients tracked, no critical shortages. "
            f"{pending} pending procurement request(s). "
            f"Category distribution: {cat_summary}. "
            f"RECOMMENDATION: Maintain current monitoring cadence; review supplier delivery rhythms weekly for proactive ordering."
        )