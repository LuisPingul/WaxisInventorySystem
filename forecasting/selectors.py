"""Shared forecast selectors — single source for consumption + radar enrichment.

Used by forecasting/views.forecast and dashboard/views.forecast_partial
to avoid duplicated enrichment logic.
"""
from django.utils import timezone

from forecasting.models import AIProcurementAlert, SupplierDeliveryPrediction
from forecasting.services import generate_all_forecasts
from forecasting.supplier_rhythm import get_upcoming_deliveries

try:
    from forecasting.dual_mode import get_dual_mode_summary
except Exception:  # pragma: no cover - dual mode optional
    get_dual_mode_summary = None


def get_enriched_rows(days_window=30, risk_filter=""):
    """Return forecast rows enriched with dual-mode intelligence."""
    rows = generate_all_forecasts(days_window=days_window)
    if risk_filter:
        rows = [r for r in rows if r["risk"] == risk_filter]
    if get_dual_mode_summary is None:
        return [{**r, "dual_mode": None} for r in rows]
    enriched = []
    for r in rows:
        try:
            dual = get_dual_mode_summary(r["ingredient"])
        except Exception:
            dual = None
        enriched.append({**r, "dual_mode": dual})
    return enriched


def get_radar_alerts(days_ahead=30, min_confidence=0.1, limit=20):
    """Return radar alerts enriched with urgency + confidence pct."""
    try:
        predictions = get_upcoming_deliveries(
            days_ahead=days_ahead, min_confidence=min_confidence
        )[:limit]
    except Exception:
        return []
    today = timezone.now().date()
    alerts = []
    for p in predictions:
        try:
            days_until = (p.predicted_window_start - today).days
        except Exception:
            days_until = 0
        urgency = "CONTACT_NOW" if days_until <= 7 else "UPCOMING"
        try:
            confidence_pct = int(float(p.confidence_score) * 100)
        except Exception:
            confidence_pct = 0
        alerts.append(
            {
                "prediction": p,
                "days_until_window": days_until,
                "urgency": urgency,
                "confidence_pct": confidence_pct,
            }
        )
    return alerts


def get_pending_alerts(limit=20):
    """Return pending AI procurement alerts with ingredient prefetched."""
    return list(
        AIProcurementAlert.objects.filter(status=AIProcurementAlert.Status.PENDING)
        .select_related("ingredient")[:limit]
    )


def count_pending_alerts():
    return AIProcurementAlert.objects.filter(
        status=AIProcurementAlert.Status.PENDING
    ).count()


def build_forecast_context(days_window=30, risk_filter="", radar_limit=20):
    """Build full context dict shared by forecast pages/partials."""
    return {
        "rows": get_enriched_rows(days_window=days_window, risk_filter=risk_filter),
        "alerts": get_pending_alerts(),
        "selected_risk": risk_filter,
        "total_alerts_pending": count_pending_alerts(),
        "radar_alerts": get_radar_alerts(limit=radar_limit),
    }


def combined_risk_for_row(row):
    """Resolve display risk: dual combined > consumption fallback."""
    dual = row.get("dual_mode") if isinstance(row, dict) else None
    if dual:
        combined = (dual.get("combined") or {}).get("combined_risk")
        if combined:
            return combined
    return row.get("risk", "LOW") if isinstance(row, dict) else "LOW"


def is_htmx(request):
    """HTMX detection compatible with django-htmx + plain headers."""
    htmx = getattr(request, "htmx", None)
    if htmx is not None:
        try:
            return bool(htmx)
        except Exception:
            pass
    return request.headers.get("HX-Request") == "true"


__all__ = [
    "SupplierDeliveryPrediction",
    "build_forecast_context",
    "combined_risk_for_row",
    "count_pending_alerts",
    "get_enriched_rows",
    "get_pending_alerts",
    "get_radar_alerts",
    "is_htmx",
]
