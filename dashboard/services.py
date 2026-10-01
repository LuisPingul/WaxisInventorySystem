from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta

from inventory.models import Ingredient, StockTransaction
from procurement.models import ProcurementRequest


def top_demanded_ingredients(days=30, limit=5):
    """Top ingredients by deduction count (Normal Usage) over rolling `days`.

    Returns Chart.js-ready {"labels": [30 day labels], "datasets": [...]},
    one zero-filled daily series per top product. All ints — JSON-safe.
    Count-based, so mixed units (kg/L/pcs) stay comparable.
    """
    since = timezone.now() - timedelta(days=days)
    base_qs = StockTransaction.objects.filter(
        transaction_type=StockTransaction.Type.DEDUCTED,
        reason=StockTransaction.Reason.NORMAL_USAGE,
        created_at__gte=since,
    )
    top = list(
        base_qs.values("ingredient__name")
        .annotate(deductions=Count("id"))
        .order_by("-deductions", "ingredient__name")[:limit]
    )
    top_names = [r["ingredient__name"] for r in top]
    if not top_names:
        return {"labels": [], "datasets": []}

    today = timezone.now().date()
    day_list = [today - timedelta(days=n) for n in range(days - 1, -1, -1)]
    day_index = {d: i for i, d in enumerate(day_list)}
    series = {name: [0] * days for name in top_names}

    daily = (
        base_qs.filter(ingredient__name__in=top_names)
        .annotate(day=TruncDate("created_at"))
        .values("ingredient__name", "day")
        .annotate(deductions=Count("id"))
    )
    for row in daily:
        idx = day_index.get(row["day"])
        if idx is not None:
            series[row["ingredient__name"]][idx] = row["deductions"]

    return {
        "labels": [d.strftime("%b %-d") for d in day_list],
        "datasets": [{"label": name, "data": series[name]} for name in top_names],
    }


def storage_distribution():
    qs = Ingredient.objects.values("category").annotate(count=Count("id"), total_qty=Sum("quantity")).order_by("category")
    qs_list = list(qs)
    # Ensure all 3 categories present even if 0
    all_categories = ["DRY", "CHILLED", "FROZEN"]
    existing = {item["category"] for item in qs_list}
    for cat in all_categories:
        if cat not in existing:
            qs_list.append({"category": cat, "count": 0, "total_qty": 0})
    # Sort by category order
    cat_order = {"DRY": 0, "CHILLED": 1, "FROZEN": 2}
    qs_list.sort(key=lambda x: cat_order.get(x["category"], 99))
    return qs_list


def dashboard_context():
    ingredients = list(Ingredient.objects.select_related("supplier_fk").all())
    total = len(ingredients)
    low = sum(1 for i in ingredients if i.status == "LOW")
    critical = sum(1 for i in ingredients if i.status in {"CRITICAL", "OUT"})
    pending = ProcurementRequest.objects.filter(status="PENDING").count()
    ordered = ProcurementRequest.objects.filter(status="ORDERED").count()
    distribution = storage_distribution()
    # Per-category product lines for doughnut tooltips (friendly labels as keys).
    label_map = {"DRY": "Dry", "CHILLED": "Chilled", "FROZEN": "Frozen"}
    chart_details = {"Dry": [], "Chilled": [], "Frozen": []}
    for ing in ingredients:
        label = label_map.get(ing.category, ing.category)
        chart_details.setdefault(label, []).append(f"{ing.name} · {ing.quantity} {ing.unit}")
    recent = StockTransaction.objects.select_related("ingredient", "user").order_by("-created_at")[:8]
    # Turnover last 7 days
    since = timezone.now() - timedelta(days=7)
    weekly = StockTransaction.objects.filter(created_at__gte=since).count()
    return {
        "ingredients": ingredients,
        "total": total,
        "low": low,
        "critical": critical,
        "pending": pending,
        "ordered": ordered,
        "distribution": distribution,
        "chart_details": chart_details,
        "recent": recent,
        "weekly_movements": weekly,
    }


def get_executive_summary_context(ctx=None):
    """
    Computes structured data for the Executive Operations Briefing.
    Provides health scores, named at-risk ingredients, supply bottlenecks,
    and prescriptive recommendations.
    """
    if ctx is None:
        ctx = dashboard_context()

    ingredients = ctx.get("ingredients", [])
    total = ctx.get("total", len(ingredients))
    low = ctx.get("low", 0)
    critical = ctx.get("critical", 0)
    pending = ctx.get("pending", 0)
    ordered = ctx.get("ordered", 0)
    distribution = ctx.get("distribution", [])

    critical_items = [i for i in ingredients if i.status in {"CRITICAL", "OUT"}]
    low_items = [i for i in ingredients if i.status == "LOW"]

    # Calculate Health Score (100 base, -8 per critical, -3 per low)
    raw_score = 100 - (len(critical_items) * 8) - (len(low_items) * 3)
    health_score = max(0, min(100, raw_score))

    if critical > 0:
        status_level = "CRITICAL"
        status_label = "Action Required"
        status_badge_class = "bg-danger text-white"
        status_icon = "bi-exclamation-octagon-fill"
        directive = "Approve high-risk procurement orders immediately to avoid stockout downtime; expedite delivery with top meat and produce suppliers."
    elif low > 0:
        status_level = "WARNING"
        status_label = "Monitoring Needed"
        status_badge_class = "bg-warning text-dark"
        status_icon = "bi-exclamation-triangle-fill"
        directive = "Review low-stock items for proactive reordering within 24–48 hours to maintain kitchen inventory safety margins."
    else:
        status_level = "HEALTHY"
        status_label = "Operations Stable"
        status_badge_class = "bg-success text-white"
        status_icon = "bi-check-circle-fill"
        directive = "Inventory levels are healthy across all categories. Continue standard weekly ordering cadence and monitor incoming shipments."

    # Perishable vs Dry Goods distribution
    perishable_count = sum(d["count"] for d in distribution if d["category"] in {"CHILLED", "FROZEN"})
    dry_count = sum(d["count"] for d in distribution if d["category"] == "DRY")

    high_risk_prs = ProcurementRequest.objects.filter(
        status="PENDING", priority__in=["CRITICAL", "HIGH"]
    ).count()

    critical_names = ", ".join([f"{i.name} ({i.quantity} {i.unit})" for i in critical_items[:3]])
    if len(critical_items) > 3:
        critical_names += f" (+{len(critical_items) - 3} more)"

    briefing_text = (
        f"⚡ *WAXI'S EXECUTIVE OPERATIONS BRIEFING*\n"
        f"Status: {status_label} (Health Score: {health_score}/100)\n\n"
        f"🚨 *Stock Health:* {critical} Critical/Out, {low} Low\n"
        f"• Depleted: {critical_names if critical_names else 'None'}\n\n"
        f"📋 *Procurement Pipeline:* {pending} Pending PRs ({high_risk_prs} High/Critical priority)\n"
        f"🧊 *Perishable Exposure:* {perishable_count} Chilled & Frozen items tracked\n\n"
        f"🎯 *Directive:* {directive}\n"
        f"— Waxi's / SND Foods International"
    )

    return {
        "health_score": health_score,
        "status_level": status_level,
        "status_label": status_label,
        "status_badge_class": status_badge_class,
        "status_icon": status_icon,
        "critical_count": critical,
        "low_count": low,
        "critical_items": critical_items[:5],
        "low_items": low_items[:4],
        "pending_count": pending,
        "ordered_count": ordered,
        "high_risk_prs": high_risk_prs,
        "perishable_count": perishable_count,
        "dry_count": dry_count,
        "distribution": distribution,
        "directive": directive,
        "briefing_text": briefing_text,
        "updated_at": timezone.now(),
    }

