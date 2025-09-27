from django.urls import path
from .views import (
    IngresosView, IngresosMensualesView,
    GastosView, GastosMensualesView,
    MorosidadView, CarteraVencidaView,
    IngresosVsGastosView, RentabilidadAreasView
)

urlpatterns = [
    path("ingresos/", IngresosView.as_view()),
    path("ingresos-mensuales/", IngresosMensualesView.as_view()),
    path("gastos/", GastosView.as_view()),
    path("gastos-mensuales/", GastosMensualesView.as_view()),
    path("morosidad/", MorosidadView.as_view()),
    path("cartera-vencida/", CarteraVencidaView.as_view()),
    path("ingresos-vs-gastos/", IngresosVsGastosView.as_view()),
    path("rentabilidad-areas/", RentabilidadAreasView.as_view()),
]
