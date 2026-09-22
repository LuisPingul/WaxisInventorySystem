from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.models import Profile
from inventory.models import Ingredient, StockTransaction
from procurement.models import ProcurementRequest

from .services import dashboard_context


def generate_executive_summary(context_dict):
    """Generate structured HTML executive summary with enumerated items and explanations."""
    total = context_dict.get("total", 0)
    low = context_dict.get("low", 0)
    critical = context_dict.get("critical", 0)
    pending = context_dict.get("pending", 0)
    distribution = context_dict.get("distribution", [])

    cat_parts = []
    for d in distribution:
        cat_name = d.get("category", "")
        cat_count = d.get("count", 0)
        if cat_count > 0:
            cat_parts.append(f"{cat_name}: {cat_count}")
    cat_summary = ", ".join(cat_parts) if cat_parts else "No category data"

    if critical > 0:
        header = '⚠️ IMMEDIATE ACTION REQUIRED'
        header_class = 'text-danger'
        recommendation = 'Approve all HIGH-risk PRs today; contact top 3 suppliers for expedited delivery on critical items.'
        rec_class = 'bg-danger-subtle border-danger'
        items = [
            ('Critical Stock', f'{critical} ingredient(s) CRITICAL/OUT of stock', 'Requires immediate procurement approval and expedited delivery'),
            ('Low Stock', f'{low} ingredient(s) below minimum threshold', 'Schedule reorders within 24 hours to prevent stockout'),
            ('Pending PRs', f'{pending} procurement request(s) awaiting approval', 'Bottleneck risk — prioritize review and approval today'),
            ('Category Breakdown', cat_summary, 'FROZEN and CHILLED items typically have shorter shelf life — monitor closely'),
        ]
    elif low > 0:
        header = '📋 MONITORING NEEDED'
        header_class = 'text-warning'
        recommendation = 'Review LOW items for reorder prioritization; ensure pending PRs are processed within 48 hours.'
        rec_class = 'bg-warning-subtle border-warning'
        items = [
            ('Low Stock', f'{low} ingredient(s) below minimum threshold', 'Schedule reorders within 48 hours to prevent escalation to critical'),
            ('Pending PRs', f'{pending} procurement request(s) awaiting approval', 'Process pending orders to maintain supply chain continuity'),
            ('Category Breakdown', cat_summary, 'Review DRY goods inventory — longest lead times typically'),
        ]
    else:
        header = '✅ INVENTORY HEALTHY'
        header_class = 'text-success'
        recommendation = 'Maintain current monitoring cadence; review supplier delivery rhythms weekly for proactive ordering.'
        rec_class = 'bg-success-subtle border-success'
        items = [
            ('Total Tracked', f'{total} ingredients across all categories', 'Full visibility maintained across DRY, CHILLED, FROZEN'),
            ('Pending PRs', f'{pending} pending procurement request(s)', 'Normal pipeline — no immediate action required'),
            ('Category Breakdown', cat_summary, 'Balanced distribution — no category over/under-represented'),
        ]

    # Build HTML
    items_html = ''.join(
        f'<li><strong>{label}:</strong> {value} — <span class="text-muted">{explanation}</span></li>'
        for label, value, explanation in items
    )

    return f'''
<div class="executive-summary">
  <h6 class="{header_class} mb-2">{header}</h6>
  <ol class="mb-3 small">{items_html}</ol>
  <div class="recommendation p-2 rounded {rec_class}">
    <strong>🎯 Recommendation:</strong> {recommendation}
  </div>
</div>
'''.strip()


@login_required
def home(request):
    """Route each authenticated user to the dashboard for their role."""
    role = getattr(getattr(request.user, "profile", None), "role", None)

    if role == Profile.Role.DEVELOPER:
        return redirect("/admin/")
    if role == Profile.Role.OWNER:
        return owner_dashboard(request)
    if role == Profile.Role.MANAGER:
        return manager_dashboard(request)
    return crew_dashboard(request)


def _inventory_summary():
    ingredients = list(Ingredient.objects.select_related("supplier_fk").all())
    return {
        "ingredients": ingredients,
        "total": len(ingredients),
        "low": sum(i.status == "LOW" for i in ingredients),
        "critical": sum(i.status in {"CRITICAL", "OUT"} for i in ingredients),
    }


def _chart_data(distribution):
    labels = [d["category"] for d in distribution]
    counts = [d["count"] for d in distribution]
    # Map friendly labels
    label_map = {"DRY": "Dry", "CHILLED": "Chilled", "FROZEN": "Frozen"}
    labels = [label_map.get(l, l) for l in labels]
    # Return a dict — templates serialize via |json_script (single encoding).
    return {"labels": labels, "counts": counts}


@login_required
def manager_dashboard(request):
    ctx = dashboard_context()
    ai_summary = None
    if request.GET.get("ai") == "1":
        snap = {"total": ctx["total"], "low": ctx["low"], "critical": ctx["critical"], "pending": ctx["pending"], "distribution": ctx["distribution"]}
        ai_summary = generate_executive_summary(snap)
    # Procurement Radar for manager (collapsible)
    from forecasting.selectors import get_radar_alerts

    radar_alerts = get_radar_alerts(days_ahead=30, min_confidence=0.1, limit=5)
    # High Demand Products for manager (deduction counts, 30d)
    try:
        from dashboard.services import top_demanded_ingredients

        demand_data = top_demanded_ingredients(days=30, limit=5)
    except Exception:
        demand_data = {"labels": [], "data": []}
    return render(request, "dashboard/manager.html", {
        "ingredients": ctx["ingredients"],
        "total": ctx["total"],
        "low": ctx["low"],
        "critical": ctx["critical"],
        "pending": ctx["pending"],
        "ordered": ctx["ordered"],
        "transactions": ctx["recent"],
        "distribution": ctx["distribution"],
        "chart_data": _chart_data(ctx["distribution"]),
        "chart_details": ctx.get("chart_details", {}),
        "demand_data": demand_data,
        "weekly_movements": ctx["weekly_movements"],
        "ai_summary": ai_summary,
        "radar_alerts": radar_alerts,
    })


@login_required
def owner_dashboard(request):
    ctx = dashboard_context()
    # Executive summary on demand (?ai=1), same as Manager dashboard
    ai_summary = None
    if request.GET.get("ai") == "1":
        snap = {"total": ctx["total"], "low": ctx["low"], "critical": ctx["critical"], "pending": ctx["pending"], "distribution": ctx["distribution"]}
        try:
            ai_summary = generate_executive_summary(snap)
        except Exception:
            ai_summary = None
    # Forecast highlights for owner
    try:
        from forecasting.selectors import get_enriched_rows

        forecast_rows = get_enriched_rows(days_window=30)[:5]
    except Exception:
        forecast_rows = []
    # Procurement Radar - upcoming supplier delivery windows
    from forecasting.selectors import get_radar_alerts as _get_radar

    radar_alerts = _get_radar(days_ahead=30, min_confidence=0.1, limit=5)
    # High Demand Products for owner (deduction counts, 30d)
    try:
        from dashboard.services import top_demanded_ingredients

        demand_data = top_demanded_ingredients(days=30, limit=5)
    except Exception:
        demand_data = {"labels": [], "data": []}
    return render(request, "dashboard/owner.html", {
        "ingredients": ctx["ingredients"],
        "total": ctx["total"],
        "low": ctx["low"],
        "critical": ctx["critical"],
        "pending": ctx["pending"],
        "ordered": ctx["ordered"],
        "transactions": StockTransaction.objects.select_related("ingredient", "user").order_by("-created_at")[:10],
        "distribution": ctx["distribution"],
        "chart_data": _chart_data(ctx["distribution"]),
        "chart_details": ctx.get("chart_details", {}),
        "demand_data": demand_data,
        "weekly_movements": ctx["weekly_movements"],
        "ai_summary": ai_summary,
        "forecast_highlights": forecast_rows,
        "radar_alerts": radar_alerts,
    })


@login_required
def ai_summary_view(request):
    ctx = dashboard_context()
    snap = {"total": ctx["total"], "low": ctx["low"], "critical": ctx["critical"], "pending": ctx["pending"], "distribution": ctx["distribution"]}
    summary = generate_executive_summary(snap)
    if request.htmx:
        return render(request, "dashboard/_ai_summary.html", {"ai_summary": summary})
    messages.info(request, summary)
    return redirect("dashboard:home")


@login_required
def crew_dashboard(request):
    transactions = StockTransaction.objects.filter(
        user=request.user
    ).select_related("ingredient")[:10]

    low = [
        i for i in Ingredient.objects.all()
        if i.status in {"LOW", "CRITICAL", "OUT"}
    ]

    return render(request, "dashboard/crew.html", {
        "transactions": transactions,
        "low": low,
        "today_count": StockTransaction.objects.filter(user=request.user).count(),
    })
