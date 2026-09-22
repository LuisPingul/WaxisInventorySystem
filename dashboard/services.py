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
