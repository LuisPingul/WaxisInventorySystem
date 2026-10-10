from django.contrib import admin
from django.urls import include, path

from dashboard.pwa_views import pwa_manifest, pwa_service_worker, pwa_offline

urlpatterns = [
    # PWA Endpoints
    path("manifest.webmanifest", pwa_manifest, name="pwa_manifest"),
    path("manifest.json", pwa_manifest, name="pwa_manifest_json"),
    path("sw.js", pwa_service_worker, name="pwa_sw"),
    path("offline/", pwa_offline, name="pwa_offline"),

    # Core Application Routes
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("dashboard.urls")),
    path("inventory/", include("inventory.urls")),
    path("procurement/", include("procurement.urls")),
    path("forecast/", include("forecasting.urls")),
    path("reports/", include("reports.urls")),
    path("audit/", include("audit.urls")),
    path("suppliers/", include("suppliers.urls")),
]
