from django.contrib.auth.models import User
from django.db import models

from inventory.models import Ingredient
from suppliers.models import Supplier


class SupplierDeliveryPrediction(models.Model):
    """Cached supplier delivery window predictions - Agrilytics output table"""
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

    def __str__(self):
        return f"{self.supplier} -> {self.ingredient}: {self.predicted_window_start} to {self.predicted_window_end} (conf: {self.confidence_score})"


class AIProcurementAlert(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CONVERTED = "CONVERTED", "Converted to Request"

    class Risk(models.TextChoices):
        HIGH = "HIGH", "High"
        MEDIUM = "MEDIUM", "Medium"
        LOW = "LOW", "Low"

    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="ai_alerts")
    suggested_quantity = models.DecimalField(max_digits=12, decimal_places=2)
    predicted_stockout_date = models.DateField(null=True, blank=True)
    daily_usage = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    days_until_stockout = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    risk = models.CharField(max_length=10, choices=Risk.choices, default=Risk.LOW)
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    # AI Variance Logging: predicted vs actual stockout
    actual_zero_date = models.DateField(null=True, blank=True, help_text="Date ingredient actually hit zero")
    variance_days = models.IntegerField(null=True, blank=True, help_text="actual - predicted days (positive = late, negative = early)")
    accuracy_note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.predicted_stockout_date and self.actual_zero_date:
            delta = self.actual_zero_date - self.predicted_stockout_date
            self.variance_days = delta.days
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "risk"]),
        ]

    def __str__(self):
        return f"Alert {self.ingredient.name} - {self.risk} - {self.suggested_quantity}"
