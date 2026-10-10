import os
from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.views.decorators.cache import cache_control


def pwa_manifest(request):
    """Serve the Web App Manifest with correct application/manifest+json MIME type."""
    manifest_path = os.path.join(settings.BASE_DIR, "static", "manifest.webmanifest")
    if not os.path.exists(manifest_path):
        raise Http404("Manifest file not found.")

    with open(manifest_path, "r", encoding="utf-8") as f:
        content = f.read()

    response = HttpResponse(content, content_type="application/manifest+json")
    response["Cache-Control"] = "public, max-age=86400"
    return response


@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def pwa_service_worker(request):
    """Serve the Service Worker script from root scope (/) with required headers."""
    sw_path = os.path.join(settings.BASE_DIR, "static", "js", "sw.js")
    if not os.path.exists(sw_path):
        raise Http404("Service worker file not found.")

    with open(sw_path, "r", encoding="utf-8") as f:
        content = f.read()

    response = HttpResponse(content, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    return response


def pwa_offline(request):
    """Render the branded offline fallback page when network is unavailable."""
    return render(request, "offline.html", status=200)
