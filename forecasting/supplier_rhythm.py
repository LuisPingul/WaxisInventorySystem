"""
Supplier Rhythm Forecasting Engine - Agrilytics Algorithm Implementation

Calculates delivery rhythm predictions based on historical inbound shipment intervals
(Inter-Arrival Time / IAT analysis) per supplier/ingredient pair.
"""
import statistics
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count
from django.utils import timezone

from inventory.models import InboundShipment
from forecasting.models import SupplierDeliveryPrediction
from suppliers.models import Supplier


MIN_DELIVERIES = 3
CONFIDENCE_THRESHOLD = Decimal("0.1")


def calculate_supplier_rhythm(supplier, ingredient, min_deliveries=MIN_DELIVERIES):
    """
    Calculate delivery rhythm for a supplier/ingredient pair using Agrilytics algorithm.
    
    Returns dict with prediction data or None if insufficient history.
    """
    shipments = InboundShipment.objects.filter(
        supplier=supplier, ingredient=ingredient
    ).order_by("received_at")

    count = shipments.count()
    if count < min_deliveries:
        return None

    # Calculate inter-arrival intervals in days
    intervals = []
    volumes = []
    shipment_list = list(shipments)
    
    for i in range(1, len(shipment_list)):
        delta = (shipment_list[i].received_at.date() - shipment_list[i-1].received_at.date()).days
        intervals.append(delta)
        volumes.append(float(shipment_list[i].quantity_received))

    # Need at least 2 intervals for std deviation
    if len(intervals) < 2:
        return None

    # Statistics using stdlib
    mean_interval = statistics.mean(intervals)
    std_interval = statistics.stdev(intervals) if len(intervals) > 1 else 0
    avg_volume = statistics.mean(volumes[-3:])  # Weight recent 3 deliveries

    last_delivery = shipment_list[-1].received_at.date()
    predicted_center = last_delivery + timedelta(days=round(mean_interval))
    buffer_days = max(2, round(std_interval))

    # Coefficient of variation -> confidence score
    cv = std_interval / mean_interval if mean_interval > 0 else 1.0
    confidence = max(0.1, min(0.99, 1.0 - (cv * 0.5)))

    return {
        "last_delivery_date": last_delivery,
        "predicted_cycle_days": round(mean_interval),
        "predicted_window_start": predicted_center - timedelta(days=buffer_days),
        "predicted_window_end": predicted_center + timedelta(days=buffer_days),
        "estimated_volume": round(avg_volume, 2),
        "confidence_score": round(confidence, 2),
    }


def compute_all_rhythms(min_deliveries=MIN_DELIVERIES, confidence_threshold=CONFIDENCE_THRESHOLD):
    """
    Compute rhythm predictions for all supplier/ingredient pairs with sufficient history.
    Upserts into SupplierDeliveryPrediction table.
    
    Returns (created_count, updated_count, skipped_count)
    """
    # Get all supplier/ingredient pairs with >= min_deliveries
    pairs = InboundShipment.objects.values("supplier", "ingredient").annotate(
        cnt=Count("id")
    ).filter(cnt__gte=min_deliveries)

    created = 0
    updated = 0
    skipped = 0

    for pair in pairs:
        supplier_id = pair["supplier"]
        ingredient_id = pair["ingredient"]
        
        supplier = Supplier.objects.get(pk=supplier_id)
        # ingredient not needed for calculation, just for FK
        
        rhythm = calculate_supplier_rhythm(supplier_id, ingredient_id, min_deliveries)
        
        if rhythm is None:
            skipped += 1
            continue

        # Check confidence threshold
        if Decimal(str(rhythm["confidence_score"])) < confidence_threshold:
            skipped += 1
            continue

        # Upsert prediction
        pred, was_created = SupplierDeliveryPrediction.objects.update_or_create(
            supplier_id=supplier_id,
            ingredient_id=ingredient_id,
            defaults={
                "last_delivery_date": rhythm["last_delivery_date"],
                "predicted_cycle_days": rhythm["predicted_cycle_days"],
                "predicted_window_start": rhythm["predicted_window_start"],
                "predicted_window_end": rhythm["predicted_window_end"],
                "estimated_volume": Decimal(str(rhythm["estimated_volume"])),
                "confidence_score": Decimal(str(rhythm["confidence_score"])),
                "status": SupplierDeliveryPrediction.Status.UPCOMING,
            }
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return created, updated, skipped


def get_upcoming_deliveries(days_ahead=30, min_confidence=CONFIDENCE_THRESHOLD):
    """
    Get upcoming delivery windows for the Procurement Radar.
    
    Args:
        days_ahead: Only show windows starting within this many days
        min_confidence: Minimum confidence score to include
    
    Returns: QuerySet of SupplierDeliveryPrediction with enriched urgency
    """
    cutoff_date = timezone.now().date() + timedelta(days=days_ahead)
    
    qs = SupplierDeliveryPrediction.objects.select_related(
        "supplier", "ingredient"
    ).filter(
        predicted_window_end__gte=timezone.now().date(),
        status=SupplierDeliveryPrediction.Status.UPCOMING,
        confidence_score__gte=min_confidence,
        predicted_window_start__lte=cutoff_date,
    ).order_by("predicted_window_start")

    return qs