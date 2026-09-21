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

Shared enrichment lives in `forecasting/selectors.py` — single source used by
both `forecasting/views.forecast` and `dashboard/views.forecast_partial`:

```python
# forecasting/selectors.py
def get_radar_alerts(days_ahead=30, min_confidence=0.1, limit=20):
    predictions = get_upcoming_deliveries(
        days_ahead=days_ahead, min_confidence=min_confidence
    )[:limit]
    ...
    # -> [{"prediction": p, "days_until_window": n,
    #      "urgency": "CONTACT_NOW"|"UPCOMING",
    #      "confidence_pct": int(...)}]
```

### Procurement Radar (HTMX Partial)
```python
# forecasting/views.py
@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def procurement_radar(request):
    enriched = get_radar_alerts(days_ahead=30, min_confidence=0.1, limit=20)
    # Preserve caller target id so hx-swap outerHTML replaces correctly
    radar_id = request.GET.get("radar_id") or request.headers.get("HX-Target") or "procurement-radar"
    return render(request, "forecasting/_procurement_radar.html", {"alerts": enriched, "radar_id": radar_id})
```

### Convert Radar Alert → ProcurementRequest
```python
@role_required(Profile.Role.DEVELOPER, Profile.Role.OWNER, Profile.Role.MANAGER)
def radar_create_pr(request, prediction_id):
    pred = get_object_or_404(SupplierDeliveryPrediction, pk=prediction_id)
    url = reverse("procurement_create") + f"?ingredient={pred.ingredient.pk}&supplier={pred.supplier.pk}&qty={pred.estimated_volume}&reason=Radar:+predicted+delivery+window+{pred.predicted_window_start}+to+{pred.predicted_window_end}&priority=HIGH"
    if is_htmx(request):
        resp = HttpResponse(status=204)
        resp["HX-Redirect"] = url  # HTMX follows via header; plain POST uses redirect()
        return resp
    return redirect(url)
```

### URL Routes
```python
# forecasting/urls.py
path("radar/", procurement_radar, name="procurement_radar"),
path("radar/<int:prediction_id>/order/", radar_create_pr, name="radar_create_pr"),
```

---

## 5. Django Template Integration (UI)

### HTMX Partial: `forecasting/_procurement_radar.html`

Brand-aligned Bootstrap cards (Waxi `#871F09`/`#FE5F10`), not Tailwind utilities.
Supports `radar_id` so owner/manager/forecast polling targets replace correctly.

```html
<div class="procurement-radar" id="{{ radar_id|default:'procurement-radar' }}">
  {% for item in alerts %}
    {% with p=item.prediction %}
    <div class="radar-card {% if item.urgency == 'CONTACT_NOW' %}urgent{% else %}soon{% endif %}">
      <div class="d-flex justify-content-between align-items-start gap-2">
        <div>
          <strong>{{ p.supplier.company_name }}</strong>
          <span class="text-muted">{{ p.ingredient.name }} ({{ p.ingredient.unit }})</span>
        </div>
        <div class="text-end">
          <span class="risk risk-{{ item.urgency|lower }}">{{ item.urgency }}</span>
          <span class="text-muted">{{ item.days_until_window }}d</span>
        </div>
      </div>
      <div class="radar-meta">
        <span>Est. <strong>{{ p.estimated_volume }} {{ p.ingredient.unit }}</strong></span>
        <span>Window <strong>{{ p.predicted_window_start|date:"M d" }}–{{ p.predicted_window_end|date:"M d" }}</strong></span>
        <span>Cycle <strong>{{ p.predicted_cycle_days }}d</strong></span>
        <span class="risk risk-low">Conf {{ item.confidence_pct }}%</span>
      </div>
      <div class="radar-actions">
        <form hx-post="{% url 'forecasting:radar_create_pr' p.pk %}" hx-swap="none">
          {% csrf_token %}
          <button type="submit" class="btn btn-sm btn-primary">
            <i class="bi bi-cart-plus me-1"></i> Lock In Order
          </button>
        </form>
      </div>
    </div>
    {% endwith %}
  {% empty %}
    <div class="empty-mini">No upcoming delivery windows predicted.</div>
  {% endfor %}
</div>
```

Shared wrappers: `forecasting/_forecast_table.html` (consumption table + Dual badges)
and `forecasting/_radar_panel.html` (panel + Refresh + optional 60s polling) are
included by both `forecasting/dashboard.html` and `forecasting/_forecast_tabs.html`
(Owner "View All" HTMX partial) — no duplicated markup.

### Dashboard Integration
- **Owner Dashboard**: Forecast Highlights show dual `combined_risk + Dual` badge; radar panel with Refresh + 90s polling (`#procurement-radar-owner`)
- **Manager Dashboard**: Radar panel with Refresh + 90s polling (`#procurement-radar-manager`)
- **Forecasting Page**: 3 tabs — Consumption Forecast (HTMX risk filter with `hx-push-url`), Supplier Radar (60s polling), Stockout Timeline (Chart.js bar colored by combined risk)

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
| React `ProcurementRadar` component | Django template partial `_procurement_radar.html` (Bootstrap + Waxi brand) |
| `Lock In Order` → POST to API | HTMX form POST → `204 + HX-Redirect` to pre-filled PR create (plain POST falls back to `redirect()`) |

The Django-native implementation is simpler, more maintainable, and leverages the existing authentication/authorization system.