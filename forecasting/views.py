from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.decorators import role_required
from accounts.models import Profile
from audit.services import log_action
from procurement.models import ProcurementRequest

from .models import AIProcurementAlert, SupplierDeliveryPrediction
from .selectors import build_forecast_context, is_htmx
from .services import generate_all_forecasts


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def forecast(request):
    risk_filter = request.GET.get("risk", "")
    ctx = build_forecast_context(days_window=30, risk_filter=risk_filter, radar_limit=20)
    if is_htmx(request):
        # Risk filter via HTMX targets #tab-consumption — return table only
        return render(request, "forecasting/_forecast_table.html", ctx)
    return render(request, "forecasting/dashboard.html", ctx)


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def generate_alerts(request):
    if request.method != "POST":
        return redirect("forecasting:forecast")
    rows = generate_all_forecasts(days_window=30)
    created = 0
    for r in rows:
        if r["risk"] in {"HIGH", "MEDIUM"} and r["reorder"] > 0:
            # Avoid duplicate pending alerts for same ingredient
            exists = AIProcurementAlert.objects.filter(
                ingredient=r["ingredient"], status=AIProcurementAlert.Status.PENDING
            ).exists()
            if exists:
                continue
            reason = f"Predicted stockout in {r['days']} days ({r['daily']}/day usage)"
            if r["ingredient"].status in {"CRITICAL", "OUT"}:
                reason = f"Critical stock: {r['ingredient'].quantity} {r['ingredient'].unit} remaining. " + reason
            AIProcurementAlert.objects.create(
                ingredient=r["ingredient"],
                suggested_quantity=r["reorder"],
                predicted_stockout_date=r["stockout_date"],
                daily_usage=r["daily"],
                days_until_stockout=r["days"],
                risk=r["risk"],
                reason=reason,
                created_by=request.user,
            )
            created += 1
    log_action(request.user, "GENERATE", "Forecasting", "", f"Generated {created} AI alerts.")
    messages.success(request, f"Generated {created} new procurement alerts (HIGH/MEDIUM risk).")
    return redirect("forecasting:forecast")


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def alerts_list(request):
    alerts = AIProcurementAlert.objects.select_related("ingredient", "created_by").order_by("-created_at")[:100]
    return render(request, "forecasting/alerts.html", {"alerts": alerts})


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def alert_approve(request, pk):
    alert = get_object_or_404(AIProcurementAlert, pk=pk)
    # Convert to ProcurementRequest
    req = ProcurementRequest.objects.create(
        ingredient=alert.ingredient,
        supplier=getattr(alert.ingredient, "supplier_fk", None),
        requested_quantity=alert.suggested_quantity,
        priority=ProcurementRequest.Priority.CRITICAL if alert.risk == "HIGH" else ProcurementRequest.Priority.HIGH,
        reason=f"AI Alert: {alert.reason}",
        requested_by=request.user,
        auto_generated=True,
    )
    alert.status = AIProcurementAlert.Status.CONVERTED
    alert.save(update_fields=["status", "updated_at"])
    log_action(request.user, "CONVERT", "Forecasting", alert.pk, f"Alert converted to PR-{req.pk:04d}")
    messages.success(request, f"Alert converted to procurement request PR-{req.pk:04d}.")
    return redirect("forecasting:forecast")


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def alert_reject(request, pk):
    alert = get_object_or_404(AIProcurementAlert, pk=pk)
    alert.status = AIProcurementAlert.Status.REJECTED
    alert.save(update_fields=["status", "updated_at"])
    log_action(request.user, "REJECT", "Forecasting", alert.pk, "AI alert rejected.")
    messages.success(request, "Alert rejected.")
    return redirect("forecasting:forecast")


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def procurement_radar(request):
    """HTMX partial: Active Hunter Radar - upcoming supplier delivery windows"""
    from .selectors import get_radar_alerts

    enriched = get_radar_alerts(days_ahead=30, min_confidence=0.1, limit=20)
    # Preserve caller target id so hx-swap outerHTML replaces correctly
    radar_id = request.GET.get("radar_id") or request.headers.get("HX-Target") or "procurement-radar"
    radar_id = str(radar_id).lstrip("#").strip() or "procurement-radar"
    return render(
        request, "forecasting/_procurement_radar.html", {"alerts": enriched, "radar_id": radar_id}
    )


@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def radar_create_pr(request, prediction_id):
    """Convert radar alert -> ProcurementRequest (pre-filled). HTMX-aware."""
    pred = get_object_or_404(SupplierDeliveryPrediction, pk=prediction_id)

    # Pre-fill PR form with predicted data
    url = reverse("procurement_create") + f"?ingredient={pred.ingredient.pk}&supplier={pred.supplier.pk}&qty={pred.estimated_volume}&reason=Radar:+predicted+delivery+window+{pred.predicted_window_start}+to+{pred.predicted_window_end}&priority=HIGH"
    if is_htmx(request):
        resp = HttpResponse(status=204)
        resp["HX-Redirect"] = url
        return resp
    return redirect(url)