"""
Dual-Mode Forecasting Intelligence

Combines consumption-based (stockout) and supplier rhythm (delivery window) forecasts
for smarter procurement decisions.
"""
from decimal import Decimal
from django.utils import timezone

from forecasting.models import SupplierDeliveryPrediction
from forecasting.services import forecast_row


def get_combined_risk(ingredient):
    """
    Get combined risk assessment from both forecasting modes.
    
    Returns dict with:
    - consumption_risk: from forecast_row (HIGH/MEDIUM/LOW)
    - rhythm_risk: from supplier rhythm (HIGH/MEDIUM/LOW/None)
    - combined_risk: adjusted risk considering both
    - sources: list of active sources ['consumption', 'rhythm', 'both']
    - recommendation: actionable text
    """
    # Consumption-based forecast (existing)
    consumption_forecast = forecast_row(ingredient)
    consumption_risk = consumption_forecast["risk"]
    
    # Supplier rhythm forecast (new)
    rhythm = SupplierDeliveryPrediction.objects.filter(
        ingredient=ingredient
    ).order_by("-confidence_score").first()
    
    rhythm_risk = None
    confidence = Decimal("0")
    
    if rhythm and rhythm.confidence_score >= Decimal("0.5"):
        confidence = rhythm.confidence_score
        days_to_window = (rhythm.predicted_window_start - timezone.now().date()).days
        
        if days_to_window <= 3 and rhythm.status == SupplierDeliveryPrediction.Status.UPCOMING:
            # Supplier delivering very soon - can tolerate lower stock
            rhythm_risk = "LOW"
        elif days_to_window <= 7 and rhythm.status == SupplierDeliveryPrediction.Status.UPCOMING:
            # Supplier delivering within a week - moderate risk
            rhythm_risk = "MEDIUM"
        elif days_to_window > 14:
            # No delivery in sight for 2+ weeks
            if consumption_risk in {"HIGH", "MEDIUM"}:
                rhythm_risk = "HIGH"
            else:
                rhythm_risk = "MEDIUM"
        else:
            rhythm_risk = "MEDIUM"
    
    # Combine risks
    sources = ["consumption"]
    combined_risk = consumption_risk
    recommendation = ""
    
    if rhythm_risk:
        sources.append("rhythm")
        
        # Risk combination logic
        risk_priority = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        
        if rhythm_risk == "LOW" and consumption_risk in {"HIGH", "MEDIUM"}:
            # Supplier delivering soon - downgrade
            combined_risk = "LOW"
            recommendation = f"Supplier delivery expected in {days_to_window} days. Stockout risk mitigated by incoming shipment."
        elif rhythm_risk == "HIGH" and consumption_risk == "LOW":
            # No delivery coming but stock OK for now
            combined_risk = "MEDIUM"
            recommendation = "No supplier delivery window in 2+ weeks. Monitor closely and prepare PR."
        elif rhythm_risk == "HIGH" and consumption_risk in {"HIGH", "MEDIUM"}:
            # Both indicate urgency
            combined_risk = "CRITICAL"
            recommendation = "CRITICAL: High consumption risk AND no supplier delivery window. Expedite procurement immediately."
        elif rhythm_risk == "MEDIUM":
            # Rhythm adds moderate concern
            if consumption_risk == "LOW":
                combined_risk = "MEDIUM"
                recommendation = "Supplier delivery window approaching. Prepare procurement request."
            else:
                combined_risk = consumption_risk
                recommendation = "Both consumption and supplier signals align. Proceed with standard procurement."
        else:
            combined_risk = max(consumption_risk, rhythm_risk, key=lambda r: risk_priority.get(r, 0))
            if not recommendation:
                recommendation = "Review both consumption forecast and supplier delivery schedule."
    else:
        sources = ["consumption"]
        if consumption_risk == "HIGH":
            recommendation = "High stockout risk. Generate procurement request immediately."
        elif consumption_risk == "MEDIUM":
            recommendation = "Moderate stockout risk. Schedule procurement within 3 days."
        else:
            recommendation = "Stock levels healthy. Continue monitoring."
    
    return {
        "consumption_risk": consumption_risk,
        "rhythm_risk": rhythm_risk,
        "combined_risk": combined_risk,
        "sources": sources,
        "confidence": float(confidence) if rhythm else 0,
        "recommendation": recommendation,
        "days_to_window": days_to_window if rhythm_risk else None,
    }


def get_dual_mode_summary(ingredient):
    """
    Get a summary dict for template display showing both forecast modes.
    """
    combined = get_combined_risk(ingredient)
    consumption = forecast_row(ingredient)
    
    rhythm = SupplierDeliveryPrediction.objects.filter(
        ingredient=ingredient
    ).order_by("-confidence_score").first()
    
    return {
        "ingredient": ingredient,
        "consumption": {
            "daily_usage": consumption["daily"],
            "days_left": consumption["days"],
            "reorder_qty": consumption["reorder"],
            "risk": consumption["risk"],
            "stockout_date": consumption["stockout_date"],
        },
        "rhythm": {
            "predicted_window_start": rhythm.predicted_window_start if rhythm else None,
            "predicted_window_end": rhythm.predicted_window_end if rhythm else None,
            "confidence": float(rhythm.confidence_score) if rhythm else 0,
            "estimated_volume": float(rhythm.estimated_volume) if rhythm else 0,
            "cycle_days": rhythm.predicted_cycle_days if rhythm else None,
            "status": rhythm.status if rhythm else None,
        } if rhythm else None,
        "combined": combined,
    }