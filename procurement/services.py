import logging
import re
from decimal import Decimal

logger = logging.getLogger(__name__)


def clean_phone_for_viber(phone):
    """
    Normalizes a phone number to standard international format for Viber URI.
    e.g. '0917-555-0101' -> '639175550101'
         '+63 917 555 0101' -> '639175550101'
    """
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    if digits.startswith("09") and len(digits) == 11:
        digits = "63" + digits[1:]
    elif digits.startswith("9") and len(digits) == 10:
        digits = "63" + digits
    return digits


def generate_po_viber(procurement_request):
    """
    Generate mobile-friendly Viber purchase order message with emoji and bold formatting.
    """
    ing = procurement_request.ingredient
    supplier = procurement_request.supplier or getattr(ing, "supplier_fk", None)
    supplier_name = getattr(supplier, "company_name", None) or getattr(ing, "supplier", "") or "Supplier"
    contact_person = getattr(supplier, "contact_person", "") or "Procurement Contact"
    lead_time = getattr(supplier, "lead_time_days", 3)
    qty = procurement_request.requested_quantity
    priority = procurement_request.priority
    category_name = ing.get_category_display() if hasattr(ing, "get_category_display") else (ing.category or "")

    priority_emoji = {
        "CRITICAL": "🚨",
        "HIGH": "⚠️",
        "NORMAL": "📦",
        "LOW": "📋",
    }.get(priority, "📦")

    priority_label = procurement_request.get_priority_display()

    cat_emoji = "🥩" if "Meat" in category_name or "Frozen" in category_name else "🥬" if "Produce" in category_name else "📦"

    message = (
        f"🍗 *PURCHASE ORDER: PR-{procurement_request.pk:04d}*\n"
        f"*Waxi's · SND Foods International*\n\n"
        f"Hello *{contact_person}* ({supplier_name}),\n\n"
        f"Good day! We would like to place an order for delivery:\n\n"
        f"{cat_emoji} *Item:* {ing.name} ({category_name})\n"
        f"⚖️ *Quantity:* {qty} {ing.unit}\n"
        f"{priority_emoji} *Priority:* {priority_label}\n"
        f"⏱️ *Required Lead Time:* {lead_time} business days\n"
    )

    if ing.quantity is not None and ing.minimum_stock is not None:
        message += f"📊 *Current Stock:* {ing.quantity} {ing.unit} (Min Threshold: {ing.minimum_stock} {ing.unit})\n"

    if procurement_request.reason:
        message += f"📝 *Order Note:* {procurement_request.reason}\n"

    message += (
        f"\nPlease reply to confirm receipt, item availability, and your estimated delivery schedule to Waxi's kitchen.\n\n"
        f"Thank you!\n"
        f"— *Waxi's Procurement Team*\n"
        f"📱 +63 917 123 9294 | ✉️ procurement@sndfoods.ph"
    )
    return message


def generate_po_email(procurement_request):
    """
    Generate PO email body using deterministic template.
    Returns (subject, body)
    """
    ing = procurement_request.ingredient
    supplier = procurement_request.supplier or getattr(ing, "supplier_fk", None)
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
        f"Dear {contact_person} at {supplier_name},\n\n"
        f"{priority_note}: We would like to place an official purchase order for "
        f"{qty} {ing.unit} of {ing.name} ({ing.get_category_display()}).\n\n"
        f"Current Inventory Status:\n"
        f"  - Current Stock: {ing.quantity} {ing.unit}\n"
        f"  - Minimum Threshold: {ing.minimum_stock} {ing.unit}\n"
        f"  - Maximum Capacity: {ing.maximum_stock} {ing.unit}\n\n"
        f"Order Details:\n"
        f"  - PR Reference: PR-{procurement_request.pk:04d}\n"
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
        f"Email: procurement@sndfoods.ph\n"
        f"Phone: +63 917 123 9294"
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