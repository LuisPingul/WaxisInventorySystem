from django.urls import path

from .views import forecast, generate_alerts, alerts_list, alert_approve, alert_reject, procurement_radar, radar_create_pr

app_name = "forecasting"

urlpatterns = [
    path("", forecast, name="forecast"),
    path("alerts/", alerts_list, name="alerts"),
    path("generate/", generate_alerts, name="generate_alerts"),
    path("alerts/<int:pk>/approve/", alert_approve, name="alert_approve"),
    path("alerts/<int:pk>/reject/", alert_reject, name="alert_reject"),
    path("radar/", procurement_radar, name="procurement_radar"),
    path("radar/<int:prediction_id>/order/", radar_create_pr, name="radar_create_pr"),
]
