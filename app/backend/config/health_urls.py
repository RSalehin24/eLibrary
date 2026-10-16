from apps.common.health import LivenessView, ReadinessView
from django.urls import path

health_routes = [
    path("health/live/", LivenessView.as_view(), name="liveness"),
    path("health/ready/", ReadinessView.as_view(), name="readiness"),
]
