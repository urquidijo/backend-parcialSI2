from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AreaComunViewSet, ReservaAreaComunViewSet

router = DefaultRouter()
router.register(r"areas", AreaComunViewSet, basename="areas")
router.register(r"reservations", ReservaAreaComunViewSet, basename="reservations")

urlpatterns = [
    path("", include(router.urls)),
]
