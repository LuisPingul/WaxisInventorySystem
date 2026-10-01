import json
from datetime import timedelta
from decimal import Decimal
from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.utils import timezone

from inventory.models import Ingredient, StockTransaction
from procurement.models import ProcurementRequest
from suppliers.models import Supplier


def resolve_time_window(range_key="30d"):
    """
    Resolves the date range filter into (range_key, start_datetime, end_datetime, label).
    Default is '30d' rolling window so data is never empty on day 1 of a month.
    """
    now = timezone.now()
    if range_key == "7d":
        start = now - timedelta(days=7)
        label = "Last 7 Days"
    elif range_key == "this_month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        label = f"This Month ({now.strftime('%B %Y')})"
    elif range_key == "last_month":
        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_of_last_month = first_of_this_month - timedelta(seconds=1)
        start = end_of_last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        now = end_of_last_month
        label = f"Last Month ({start.strftime('%B %Y')})"
    elif range_key == "ytd":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        label = f"Year to Date ({now.year})"
    elif range_key == "all":
        start = None
        label = "All Recorded Time"
    else:
        range_key = "30d"
        start = now - timedelta(days=30)
        label = "Last 30 Days (Rolling)"

    return range_key, start, now, label


def get_executive_financials(start_datetime, end_datetime):
    """
    Calculates primary financial valuation, procurement expenditures,
    and monetary food waste loss (SDG 12).
    """
    # 1. Total Current Stock Capital Valuation
    total_inventory_value = (
        Ingredient.objects.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F("quantity") * F("unit_cost"),
                    output_field=DecimalField(max_digits=20, decimal_places=2),
                )
            )
        )["total"]
        or Decimal("0.00")
    )

    # 2. Procurement Spend in Time Window
    pr_qs = ProcurementRequest.objects.exclude(status=ProcurementRequest.Status.REJECTED)
    if start_datetime:
        pr_qs = pr_qs.filter(created_at__gte=start_datetime, created_at__lte=end_datetime)

    procurement_spend = Decimal("0.00")
    for pr in pr_qs.select_related("ingredient"):
        price = (
            pr.unit_price
            if pr.unit_price and pr.unit_price > 0
            else (getattr(pr.ingredient, "unit_cost", None) or Decimal("0.00"))
        )
        procurement_spend += (pr.requested_quantity or Decimal("0.00")) * price

    # 3. Spoilage & Shrinkage (SDG 12)
    tx_qs = StockTransaction.objects.all()
    if start_datetime:
        tx_qs = tx_qs.filter(created_at__gte=start_datetime, created_at__lte=end_datetime)

    total_tx_count = tx_qs.count()

    spoilage_filter = Q(transaction_type=StockTransaction.Type.SPOILAGE) | Q(
        reason__in=[
            StockTransaction.Reason.SPOILAGE_WASTE,
            StockTransaction.Reason.DAMAGED,
        ]
    )
    spoilage_qs = tx_qs.filter(spoilage_filter).select_related("ingredient")

    spoilage_count = spoilage_qs.count()
    spoilage_cost = Decimal("0.00")
    spoilage_qty = Decimal("0.00")
    for st in spoilage_qs:
        unit_cost = getattr(st.ingredient, "unit_cost", None) or Decimal("0.00")
        spoilage_cost += (st.quantity or Decimal("0.00")) * unit_cost
        spoilage_qty += (st.quantity or Decimal("0.00"))

    spoilage_rate = (
        round((spoilage_count / total_tx_count) * 100, 1) if total_tx_count > 0 else 0.0
    )

    return {
        "total_inventory_value": total_inventory_value,
        "procurement_spend": procurement_spend,
        "procurement_count": pr_qs.count(),
        "spoilage_cost": spoilage_cost,
        "spoilage_qty": spoilage_qty,
        "spoilage_count": spoilage_count,
        "spoilage_rate": spoilage_rate,
        "total_tx_count": total_tx_count,
        "total_ingredients_count": Ingredient.objects.count(),
    }


def get_spoilage_breakdown(start_datetime, end_datetime):
    """
    Detailed waste & shrinkage breakdown by reason (Damaged, Expired, Spoilage)
    and top spoiled items for SDG 12 mitigation.
    """
    tx_qs = StockTransaction.objects.all()
    if start_datetime:
        tx_qs = tx_qs.filter(created_at__gte=start_datetime, created_at__lte=end_datetime)

    spoilage_filter = Q(transaction_type=StockTransaction.Type.SPOILAGE) | Q(
        reason__in=[
            StockTransaction.Reason.SPOILAGE_WASTE,
            StockTransaction.Reason.DAMAGED,
        ]
    )
    spoilage_qs = tx_qs.filter(spoilage_filter).select_related("ingredient")

    by_reason_map = {}
    item_map = {}

    for st in spoilage_qs:
        reason_label = st.get_reason_display() or "Other Waste"
        cost = (st.quantity or Decimal("0.00")) * (getattr(st.ingredient, "unit_cost", None) or Decimal("0.00"))

        if reason_label not in by_reason_map:
            by_reason_map[reason_label] = {"count": 0, "cost": Decimal("0.00"), "qty": Decimal("0.00")}
        by_reason_map[reason_label]["count"] += 1
        by_reason_map[reason_label]["cost"] += cost
        by_reason_map[reason_label]["qty"] += st.quantity or Decimal("0.00")

        ing_id = st.ingredient_id
        if ing_id not in item_map:
            item_map[ing_id] = {
                "name": st.ingredient.name,
                "category": st.ingredient.get_category_display() if hasattr(st.ingredient, "get_category_display") else st.ingredient.category,
                "unit": st.ingredient.unit,
                "count": 0,
                "qty": Decimal("0.00"),
                "cost": Decimal("0.00"),
            }
        item_map[ing_id]["count"] += 1
        item_map[ing_id]["qty"] += st.quantity or Decimal("0.00")
        item_map[ing_id]["cost"] += cost

    top_spoiled = sorted(item_map.values(), key=lambda x: x["cost"], reverse=True)[:5]
    reasons_list = [
        {"reason": k, "count": v["count"], "cost": v["cost"], "qty": v["qty"]}
        for k, v in by_reason_map.items()
    ]

    return {
        "reasons": sorted(reasons_list, key=lambda x: x["cost"], reverse=True),
        "top_spoiled": top_spoiled,
    }


def get_velocity_analytics(start_datetime, end_datetime):
    """
    Identifies Top 5 Fast Movers (highest usage volume) and
    Dead / Slow-Moving Stock (zero deductions in last 30 days).
    """
    tx_qs = StockTransaction.objects.filter(
        transaction_type__in=[
            StockTransaction.Type.DEDUCTED,
            StockTransaction.Type.SPOILAGE,
        ]
    )
    if start_datetime:
        tx_qs = tx_qs.filter(created_at__gte=start_datetime, created_at__lte=end_datetime)

    fast_movers_qs = (
        tx_qs.values("ingredient__name", "ingredient__unit", "ingredient__category")
        .annotate(total_deducted=Sum("quantity"), tx_count=Count("id"))
        .order_by("-total_deducted")[:5]
    )

    fast_movers = [
        {
            "name": r["ingredient__name"],
            "unit": r["ingredient__unit"],
            "category": r["ingredient__category"],
            "total_deducted": r["total_deducted"],
            "tx_count": r["tx_count"],
        }
        for r in fast_movers_qs
    ]

    # Dead Stock: 0 deductions in the last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    moved_ingredient_ids = (
        StockTransaction.objects.filter(
            transaction_type__in=[
                StockTransaction.Type.DEDUCTED,
                StockTransaction.Type.SPOILAGE,
            ],
            created_at__gte=thirty_days_ago,
        )
        .values_list("ingredient_id", flat=True)
        .distinct()
    )

    dead_qs = Ingredient.objects.exclude(id__in=moved_ingredient_ids).select_related("supplier_fk")
    dead_stock = []
    for ing in dead_qs:
        unit_cost = ing.unit_cost or Decimal("0.00")
        tied_capital = (ing.quantity or Decimal("0.00")) * unit_cost
        dead_stock.append({
            "name": ing.name,
            "category": ing.get_category_display() if hasattr(ing, "get_category_display") else ing.category,
            "quantity": ing.quantity,
            "unit": ing.unit,
            "unit_cost": unit_cost,
            "capital_tied": tied_capital,
            "supplier": ing.supplier_fk.company_name if ing.supplier_fk else (ing.supplier or "No Supplier"),
            "status": ing.status,
        })

    # Sort dead stock by highest capital tied up first
    dead_stock.sort(key=lambda x: x["capital_tied"], reverse=True)

    return {
        "fast_movers": fast_movers,
        "dead_stock": dead_stock[:10],
        "dead_stock_total_value": sum((d["capital_tied"] for d in dead_stock), Decimal("0.00")),
        "dead_stock_count": len(dead_stock),
    }


def get_storage_capital_breakdown():
    """
    Calculates capital allocation by storage category (Frozen, Chilled, Dry).
    Maps to Waxi's brand-locked palette.
    """
    category_colors = {
        "Frozen": "#871F09",   # Brand Maroon
        "Chilled": "#FE5F10",  # Brand Electric Orange
        "Dry Goods": "#FED216", # Brand Warm Amber
        "Dry": "#FED216",
        "Produce": "#15803D",  # Emerald Green
        "Other": "#64748B",
    }

    ingredients = Ingredient.objects.all()
    cat_map = {}

    for ing in ingredients:
        cat_label = ing.get_category_display() if hasattr(ing, "get_category_display") else (ing.category or "Other")
        cost = (ing.quantity or Decimal("0.00")) * (ing.unit_cost or Decimal("0.00"))

        if cat_label not in cat_map:
            cat_map[cat_label] = {
                "count": 0,
                "capital": Decimal("0.00"),
                "color": category_colors.get(cat_label, "#64748B"),
            }
        cat_map[cat_label]["count"] += 1
        cat_map[cat_label]["capital"] += cost

    labels = list(cat_map.keys())
    capitals = [float(cat_map[l]["capital"]) for l in labels]
    counts = [cat_map[l]["count"] for l in labels]
    colors = [cat_map[l]["color"] for l in labels]

    chart_category = json.dumps({
        "labels": labels,
        "capitals": capitals,
        "counts": counts,
        "colors": colors,
    })

    summary_list = [
        {
            "category": l,
            "count": cat_map[l]["count"],
            "capital": cat_map[l]["capital"],
            "color": cat_map[l]["color"],
        }
        for l in labels
    ]

    return {
        "chart_json": chart_category,
        "categories": sorted(summary_list, key=lambda x: x["capital"], reverse=True),
    }


def get_daily_consumption_trend(start_datetime, end_datetime):
    """
    Returns daily usage and waste trends for Chart.js in the selected time window.
    """
    tx_qs = StockTransaction.objects.filter(
        transaction_type__in=[
            StockTransaction.Type.DEDUCTED,
            StockTransaction.Type.SPOILAGE,
        ]
    )
    if start_datetime:
        tx_qs = tx_qs.filter(created_at__gte=start_datetime, created_at__lte=end_datetime)

    daily_map = {}
    for st in tx_qs:
        day_str = st.created_at.strftime("%b %d")
        if day_str not in daily_map:
            daily_map[day_str] = {"deductions": 0, "spoilage": 0}
        if st.transaction_type == StockTransaction.Type.SPOILAGE:
            daily_map[day_str]["spoilage"] += 1
        else:
            daily_map[day_str]["deductions"] += 1

    days = list(daily_map.keys())[-14:] # Last 14 active days
    deductions = [daily_map[d]["deductions"] for d in days]
    spoilage = [daily_map[d]["spoilage"] for d in days]

    return json.dumps({
        "labels": days,
        "deductions": deductions,
        "spoilage": spoilage,
    })


def get_supplier_performance(start_datetime, end_datetime):
    """
    Computes vendor fulfillment scorecards:
    On-time delivery percentage, average delay in days, and total spend.
    """
    suppliers = Supplier.objects.filter(is_active=True)
    metrics = []

    for sup in suppliers:
        delivered_qs = ProcurementRequest.objects.filter(
            supplier=sup,
            status=ProcurementRequest.Status.DELIVERED,
        )
        if start_datetime:
            delivered_qs = delivered_qs.filter(created_at__gte=start_datetime, created_at__lte=end_datetime)

        total_delivered = delivered_qs.count()
        delays = []
        on_time_count = 0
        total_spend = Decimal("0.00")

        for pr in delivered_qs.select_related("ingredient"):
            price = pr.unit_price if pr.unit_price and pr.unit_price > 0 else (getattr(pr.ingredient, "unit_cost", None) or Decimal("0.00"))
            total_spend += (pr.delivered_quantity or pr.requested_quantity or Decimal("0.00")) * price

            exp = pr.expected_delivery_date or pr.expected_date
            act = pr.actual_delivery_date
            if exp and act:
                delay = (act - exp).days
                delays.append(delay)
                if delay <= 0:
                    on_time_count += 1

        avg_delay = round(sum(delays) / len(delays), 1) if delays else sup.lead_time_days
        on_time_rate = round((on_time_count / len(delays)) * 100, 1) if delays else 100.0
        is_reliable = avg_delay <= 2

        metrics.append({
            "name": sup.company_name,
            "contact_person": sup.contact_person,
            "phone": sup.phone,
            "email": sup.email,
            "lead_time_days": sup.lead_time_days,
            "avg_delay": avg_delay,
            "on_time_rate": on_time_rate,
            "total_delivered": total_delivered,
            "total_spend": total_spend,
            "is_reliable": is_reliable,
            "status_label": "Reliable" if is_reliable else "Delayed",
        })

    metrics.sort(key=lambda x: (not x["is_reliable"], x["avg_delay"]))
    return metrics
