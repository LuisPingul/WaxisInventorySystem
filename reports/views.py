import csv
from decimal import Decimal
from django.http import HttpResponse
from django.shortcuts import render

from accounts.decorators import role_required
from accounts.models import Profile
from config.security import sanitize_csv_cell
from inventory.models import Ingredient, StockTransaction
from procurement.models import ProcurementRequest

from .services import (
    resolve_time_window,
    get_executive_financials,
    get_spoilage_breakdown,
    get_velocity_analytics,
    get_storage_capital_breakdown,
    get_daily_consumption_trend,
    get_supplier_performance,
)

# Both Manager and Owner have full operational and executive access to all inventory reports
REPORTS_MANAGEMENT = (
    Profile.Role.DEVELOPER,
    Profile.Role.OWNER,
    Profile.Role.MANAGER,
)


@role_required(*REPORTS_MANAGEMENT)
def reports(request):
    range_key = request.GET.get("range", "30d")
    active_tab = request.GET.get("tab", "overview")
    if active_tab not in {"overview", "velocity", "spoilage", "suppliers"}:
        active_tab = "overview"

    # Resolve time range
    range_key, start_date, end_date, range_label = resolve_time_window(range_key)

    # Core analytics
    financials = get_executive_financials(start_date, end_date)
    spoilage = get_spoilage_breakdown(start_date, end_date)
    velocity = get_velocity_analytics(start_date, end_date)
    storage = get_storage_capital_breakdown()
    daily_trend_json = get_daily_consumption_trend(start_date, end_date)
    supplier_metrics = get_supplier_performance(start_date, end_date)

    # Ingredients & Recent activity
    recent_transactions = StockTransaction.objects.select_related("ingredient", "user").order_by("-created_at")[:25]
    recent_procurements = ProcurementRequest.objects.select_related("ingredient", "supplier").order_by("-created_at")[:25]

    context = {
        # Time window
        "range_key": range_key,
        "range_label": range_label,
        "active_tab": active_tab,

        # Financials
        "total_inventory_value": financials["total_inventory_value"],
        "procurement_spend": financials["procurement_spend"],
        "procurement_count": financials["procurement_count"],
        "spoilage_cost": financials["spoilage_cost"],
        "spoilage_qty": financials["spoilage_qty"],
        "spoilage_count": financials["spoilage_count"],
        "spoilage_rate": financials["spoilage_rate"],
        "total_tx_count": financials["total_tx_count"],
        "total_ingredients": financials["total_ingredients_count"],

        # Movement & Velocity
        "fast_movers": velocity["fast_movers"],
        "dead_stock": velocity["dead_stock"],
        "dead_stock_total_value": velocity["dead_stock_total_value"],
        "dead_stock_count": velocity["dead_stock_count"],

        # Spoilage & SDG 12
        "spoilage_reasons": spoilage["reasons"],
        "top_spoiled": spoilage["top_spoiled"],

        # Storage & Categories
        "chart_category": storage["chart_json"],
        "category_breakdown": storage["categories"],

        # Daily Trend Chart
        "daily_trend_json": daily_trend_json,

        # Suppliers
        "supplier_metrics": supplier_metrics,

        # Recent activities
        "transactions": recent_transactions,
        "procurements": recent_procurements,
    }

    return render(request, "reports/dashboard.html", context)


@role_required(*REPORTS_MANAGEMENT)
def reports_export(request):
    """
    Comprehensive CSV export for the selected date range.
    Accessible to both Manager and Owner.
    """
    range_key = request.GET.get("range", "30d")
    range_key, start_date, end_date, range_label = resolve_time_window(range_key)

    financials = get_executive_financials(start_date, end_date)
    velocity = get_velocity_analytics(start_date, end_date)
    spoilage = get_spoilage_breakdown(start_date, end_date)
    suppliers = get_supplier_performance(start_date, end_date)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="inventiq_report_{range_key}_{end_date:%Y%m%d}.csv"'
    response["X-Content-Type-Options"] = "nosniff"

    raw_writer = csv.writer(response)

    def write_safe_row(cells):
        raw_writer.writerow([sanitize_csv_cell(c) for c in cells])

    write_safe_row(["INVENTIQ EXECUTIVE INVENTORY REPORT", f"Generated: {end_date:%Y-%m-%d %H:%M}"])
    write_safe_row(["Time Window", range_label])
    write_safe_row([])

    # Financial Valuation
    write_safe_row(["1. FINANCIAL VALUATION & BUDGET"])
    write_safe_row(["Total Current Stock Value (PHP)", f"{financials['total_inventory_value']:.2f}"])
    write_safe_row(["Procurement Spend (PHP)", f"{financials['procurement_spend']:.2f}"])
    write_safe_row(["Procurement Orders Count", financials["procurement_count"]])
    write_safe_row(["Total Waste Loss (PHP)", f"{financials['spoilage_cost']:.2f}"])
    write_safe_row(["Spoilage & Waste Rate (%)", f"{financials['spoilage_rate']}%"])
    write_safe_row([])

    # Fast Movers
    write_safe_row(["2. TOP FAST-MOVING INGREDIENTS"])
    write_safe_row(["Ingredient", "Category", "Total Consumed", "Unit", "Deduction Count"])
    for fm in velocity["fast_movers"]:
        write_safe_row([fm["name"], fm["category"], f"{fm['total_deducted']:.2f}", fm["unit"], fm["tx_count"]])
    write_safe_row([])

    # Dead Stock
    write_safe_row(["3. DEAD / SLOW-MOVING STOCK (Zero movement in 30 days)"])
    write_safe_row(["Ingredient", "Category", "Current Stock", "Unit Cost (PHP)", "Capital Tied (PHP)", "Assigned Supplier"])
    for ds in velocity["dead_stock"]:
        write_safe_row([ds["name"], ds["category"], f"{ds['quantity']} {ds['unit']}", f"{ds['unit_cost']:.2f}", f"{ds['capital_tied']:.2f}", ds["supplier"]])
    write_safe_row([])

    # Spoilage Root Causes
    write_safe_row(["4. FOOD SPOILAGE & SHRINKAGE BREAKDOWN (SDG 12)"])
    write_safe_row(["Reason", "Incidents Count", "Quantity Lost", "Total Cost Loss (PHP)"])
    for sr in spoilage["reasons"]:
        write_safe_row([sr["reason"], sr["count"], f"{sr['qty']:.2f}", f"{sr['cost']:.2f}"])
    write_safe_row([])

    # Supplier Performance
    write_safe_row(["5. SUPPLIER FULFILLMENT & ON-TIME RELIABILITY"])
    write_safe_row(["Supplier", "Total Delivered POs", "On-Time Rate (%)", "Avg Delay (Days)", "Total Spend (PHP)", "Reliability Status"])
    for sm in suppliers:
        write_safe_row([
            sm["name"],
            sm["total_delivered"],
            f"{sm['on_time_rate']}%",
            f"{sm['avg_delay']} days",
            f"{sm['total_spend']:.2f}",
            sm["status_label"],
        ])

    return response
