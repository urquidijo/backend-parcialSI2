from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PropertyViewSet

router = DefaultRouter()
router.register(r'properties', PropertyViewSet, basename='properties')

urlpatterns = [
    path("", include(router.urls)),
    path("api/payments/", include("payments.urls")),
]
