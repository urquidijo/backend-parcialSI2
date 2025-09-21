# commons/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AreaComunViewSet, ReservaAreaComunViewSet
from .views_reports import usage_report   # <-- importa la vista del reporte

router = DefaultRouter()
router.register(r"areas", AreaComunViewSet, basename="areas")
router.register(r"reservations", ReservaAreaComunViewSet, basename="reservations")

urlpatterns = [
    path("", include(router.urls)),                 # <-- montar router
    path("reports/usage/", usage_report, name="usage-report"),  # <-- endpoint del reporte
]
