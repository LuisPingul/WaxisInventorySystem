from django.contrib import admin

from .models import AIProcurementAlert, SupplierDeliveryPrediction


@admin.register(AIProcurementAlert)
class AIProcurementAlertAdmin(admin.ModelAdmin):
    list_display = ("id", "ingredient", "risk", "days_until_stockout", "suggested_quantity", "status", "created_at")
    list_filter = ("risk", "status")
    search_fields = ("ingredient__name", "reason")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SupplierDeliveryPrediction)
class SupplierDeliveryPredictionAdmin(admin.ModelAdmin):
    list_display = ("supplier", "ingredient", "last_delivery_date", "predicted_cycle_days", "predicted_window_start", "predicted_window_end", "estimated_volume", "confidence_score", "status", "updated_at")
    list_filter = ("status", "supplier")
    search_fields = ("supplier__company_name", "ingredient__name")
    readonly_fields = ("updated_at",)
    ordering = ["-updated_at"]
