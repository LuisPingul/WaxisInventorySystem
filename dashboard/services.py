from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta

from inventory.models import Ingredient, StockTransaction
from procurement.models import ProcurementRequest


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
        "recent": recent,
        "weekly_movements": weekly,
    }
