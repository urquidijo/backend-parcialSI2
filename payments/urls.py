# backend/payments/urls.py
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    PriceConfigViewSet,
    ChargeViewSet,
    create_checkout_session,
    stripe_webhook,
    MyChargesViewSet,
    reconcile_payment,
)
from .views_reports import payments_report

router = DefaultRouter()
router.register(r"price-configs", PriceConfigViewSet, basename="price-configs")
router.register(r"charges", ChargeViewSet, basename="charges")
router.register(r"my-charges", MyChargesViewSet, basename="my-charges") 

urlpatterns = [
    path("create-checkout-session/", create_checkout_session, name="create-checkout-session"),
    path("stripe/webhook/", stripe_webhook, name="stripe-webhook"),
    path("reconcile/<int:pk>/", reconcile_payment, name="reconcile-payment"),

    # 🔹 Reporte de pagos (JSON/CSV)
    path("reports/", payments_report, name="payments-report"),
]

urlpatterns += router.urls
