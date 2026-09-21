# AGRILYTICS: Predictive Procurement AI - Django Integration Guide

This document describes the **actual implemented** integration of the Agrilytics Predictive Procurement Engine into the WaxisInventorySystem (Django monolith).

## 1. System Architecture Overview

The Agrilytics engine is integrated as a **Django management command + service module** within the existing Django monolith (not a separate Node.js/Python worker + React frontend as originally planned).

**Actual Stack:** PostgreSQL (Supabase), Django 4.2 LTS, HTMX, Chart.js (CDN), Bootstrap 5.

---

## 2. Database Schema

### 2.1 Source Data Table: `InboundShipment` (Django Model)

Historical inbound delivery records sourced from `ProcurementRequest` (DELIVERED/ORDERED) and `StockTransaction` (ADDED).

```python
class InboundShipment(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="inbound_shipments")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="inbound_shipments")
    procurement_request = models.ForeignKey(ProcurementRequest, on_delete=models.SET_NULL, null=True, blank=True)
    quantity_received = models.DecimalField(max_digits=12, decimal_places=2)
    received_at = models.DateTimeField()
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["supplier", "ingredient", "received_at"]),
            models.Index(fields=["received_at"]),
        ]
        ordering = ["-received_at"]
```

### 2.2 Predictive Output Table: `SupplierDeliveryPrediction` (Django Model)

Cached supplier delivery window predictions — Agrilytics output table.

```python
class SupplierDeliveryPrediction(models.Model):
    class Status(models.TextChoices):
        UPCOMING = "UPCOMING", "Upcoming"
        ACTIVE = "ACTIVE", "Active Window"
        MISSED = "MISSED", "Window Missed"

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="delivery_predictions")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="delivery_predictions")
    last_delivery_date = models.DateField()
    predicted_cycle_days = models.PositiveIntegerField()
    predicted_window_start = models.DateField()
    predicted_window_end = models.DateField()
    estimated_volume = models.DecimalField(max_digits=12, decimal_places=2)
    confidence_score = models.DecimalField(max_digits=3, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPCOMING)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["supplier", "ingredient"]
        indexes = [
            models.Index(fields=["predicted_window_start", "status"]),
            models.Index(fields=["confidence_score"]),
        ]
```

---

## 3. Python Forecasting Engine (Django Service)

Located in `forecasting/supplier_rhythm.py`. Runs via `manage.py compute_forecasts` cron.

```python
def calculate_supplier_rhythm(supplier, ingredient, min_deliveries=3):
    """Agrilytics core algorithm - Inter-Arrival Time analysis"""
    shipments = InboundShipment.objects.filter(
        supplier=supplier, ingredient=ingredient
    ).order_by("received_at")
    
    if shipments.count() < min_deliveries:
        return None
    
    intervals = []
    volumes = []
    shipment_list = list(shipments)
    
    for i in range(1, len(shipment_list)):
        delta = (shipment_list[i].received_at.date() - shipment_list[i-1].received_at.date()).days
        intervals.append(delta)
        volumes.append(float(shipment_list[i].quantity_received))
    
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
```

### Cron Integration

```bash
# Daily cron (02:00)
0 2 * * * python manage.py compute_forecasts

# Standalone rhythm refresh
python manage.py compute_forecasts --rhythm-only
```

---

## 4. Django API Endpoints (HTMX Partials)

### Procurement Radar (HTMX Partial)
```python
# forecasting/views.py
@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def procurement_radar(request):
    predictions = get_upcoming_deliveries(days_ahead=30, min_confidence=0.1)
    
    enriched = []
    for p in predictions:
        days_until = (p.predicted_window_start - timezone.now().date()).days
        urgency = "CONTACT_NOW" if days_until <= 7 else "UPCOMING"
        enriched.append({
            "prediction": p,
            "days_until_window": days_until,
            "urgency": urgency,
            "confidence_pct": int(p.confidence_score * 100),
        })
    
    return render(request, "forecasting/_procurement_radar.html", {"alerts": enriched})
```

### Convert Radar Alert → ProcurementRequest
```python
@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def radar_create_pr(request, prediction_id):
    pred = get_object_or_404(SupplierDeliveryPrediction, pk=prediction_id)
    url = reverse("procurement_create") + f"?ingredient={pred.ingredient.pk}&supplier={pred.supplier.pk}&qty={pred.estimated_volume}&reason=Radar:+predicted+delivery+window+{pred.predicted_window_start}+to+{pred.predicted_window_end}&priority=HIGH"
    return redirect(url)
```

### URL Routes
```python
# forecasting/urls.py
path("radar/", procurement_radar, name="procurement_radar"),
path("radar/<int:pk>/order/", radar_create_pr, name="radar_create_pr"),
```

---

## 5. Django Template Integration (UI)

### HTMX Partial: `forecasting/_procurement_radar.html`
```html
<div class="procurement-radar" id="procurement-radar">
  {% if alerts %}
    <div class="space-y-2">
      {% for item in alerts %}
        {% with p=item.prediction %}
          <div class="p-3 border-l-4 rounded-r 
            {% if item.urgency == 'CONTACT_NOW' %}border-red-500 bg-red-50{% else %}border-blue-500 bg-blue-50{% endif %}">
            <div class="flex justify-between items-start">
              <div>
                <strong class="text-sm">{{ p.supplier.company_name }}</strong>
                <span class="text-xs text-gray-500 ml-2">{{ p.ingredient.name }} ({{ p.ingredient.unit }})</span>
              </div>
              <div class="text-right">
                <span class="inline-block px-2 py-0.5 text-xs font-semibold rounded 
                  {% if item.urgency == 'CONTACT_NOW' %}bg-red-100 text-red-700{% else %}bg-blue-100 text-blue-700{% endif %}">
                  {{ item.urgency }}
                </span>
                <span class="ml-2 text-xs text-gray-600">{{ item.days_until_window }} days</span>
              </div>
            </div>
            <div class="mt-1 flex flex-wrap gap-3 text-xs text-gray-700">
              <span>Est. Volume: <strong>{{ p.estimated_volume }} {{ p.ingredient.unit }}</strong></span>
              <span>Window: <strong>{{ p.predicted_window_start|date:"M d" }} - {{ p.predicted_window_end|date:"M d" }}</strong></span>
              <span>Cycle: <strong>{{ p.predicted_cycle_days }}d</strong></span>
              <span class="px-2 py-0.5 bg-gray-200 rounded">Conf: {{ item.confidence_pct }}%</span>
            </div>
            <div class="mt-2">
              <form hx-post="{% url 'forecasting:radar_create_pr' p.pk %}" hx-target="#procurement-radar" hx-swap="outerHTML">
                {% csrf_token %}
                <button type="submit" class="btn btn-sm {% if item.urgency == 'CONTACT_NOW' %}btn-danger{% else %}btn-primary{% endif %}">
                  <i class="bi bi-cart-plus me-1"></i> Lock In Order
                </button>
              </form>
            </div>
          </div>
        {% endwith %}
      {% endfor %}
    </div>
  {% else %}
    <div class="text-center py-4 text-gray-500">No upcoming delivery windows predicted.</div>
  {% endif %}
</div>
```

### Dashboard Integration
- **Owner Dashboard**: Full panel with top 5 predictions
- **Manager Dashboard**: Collapsible panel with top 5 predictions  
- **Forecasting Page**: Dedicated "Supplier Radar" tab with all predictions

---

## 6. Data Backfill

```bash
# Populate InboundShipment from historical data (3 priority sources)
python manage.py backfill_inbound_shipments [--dry-run] [--clear] [--source=all|delivered|ordered|stock]
```

Sources (priority order):
1. `ProcurementRequest` DELIVERED with `actual_delivery_date` (highest confidence)
2. `ProcurementRequest` ORDERED with `expected_delivery_date`
3. `StockTransaction` ADDED with `ingredient.supplier_fk`

---

## 7. Dual-Mode Intelligence

The system combines two forecasting modes:

| Mode | Source | Output |
|------|--------|--------|
| **Consumption Forecast** | `StockTransaction` (DEDUCTED/SPOILAGE) | Stockout date, daily usage, risk level |
| **Supplier Rhythm** | `InboundShipment` | Delivery window, estimated volume, confidence |

**Combined Logic** (`forecasting/dual_mode.py`):
- If supplier delivering soon (≤7 days): downgrade consumption risk
- If no delivery window in 14+ days & HIGH consumption risk: escalate to CRITICAL
- Both signals shown in forecasting table with "Dual" badge

---

## 8. Management Commands

| Command | Purpose |
|---------|---------|
| `backfill_inbound_shipments` | One-time historical data load from PRs + StockTransaction |
| `compute_forecasts` | Daily: consumption alerts + supplier rhythms |
| `compute_forecasts --rhythm-only` | Standalone rhythm refresh |

---

## 9. Key Differences from Original Plan

| Original Plan | Actual Implementation |
|---------------|----------------------|
| Node.js/Express API | Django HTMX partials |
| React frontend | Django templates + HTMX |
| Separate Python worker | Django management command |
| REST API + React | HTMX partials + template includes |
| `numpy` for stats | Python `statistics` module (stdlib) |
| Separate cache table | Django model `SupplierDeliveryPrediction` |
| React `ProcurementRadar` component | Django template partial `_procurement_radar.html` |
| `Lock In Order` → POST to API | HTMX form POST → redirect to PR create |

The Django-native implementation is simpler, more maintainable, and leverages the existing authentication/authorization system.