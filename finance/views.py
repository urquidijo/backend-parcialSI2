from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum, Count, Avg, F
from django.db.models.functions import TruncMonth
from payments.models import Payment, Charge, PriceConfig
from maintenance.models import Reporte
from commons.models import AreaComun, ReservaAreaComun
from condominio.models import Property



# === INGRESOS ===
class IngresosView(APIView):
    """Ingresos totales y por tipo de cobro"""
    def get(self, request):
        total = Payment.objects.filter(status="SUCCEEDED").aggregate(
            total=Sum("amount")
        )["total"] or 0

        por_tipo = (
            Charge.objects
            .values(tipo=F("price_config__type"))
            .annotate(total=Sum("price_config__base_price"))
        )

        data = [{"name": "Total Ingresos", "value": float(total)}]
        for item in por_tipo:
            data.append({"name": item["tipo"], "value": float(item["total"])})
        return Response(data)


class IngresosMensualesView(APIView):
    """Flujo de caja mensual (según fecha de los cargos asociados)"""
    def get(self, request):
        ingresos = (
            Payment.objects.filter(status="SUCCEEDED")
            .select_related("charge")  # para traer el cargo relacionado
            .values("charge__fecha_pago")
            .annotate(month=TruncMonth("charge__fecha_pago"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )
        data = [
            {"month": i["month"].strftime("%Y-%m"), "total": float(i["total"])}
            for i in ingresos if i["month"] is not None
        ]
        return Response(data)


# === GASTOS ===
class GastosView(APIView):
    """Gastos totales y promedio"""
    def get(self, request):
        total = Reporte.objects.aggregate(total=Sum("costo_total"))["total"] or 0
        promedio = Reporte.objects.aggregate(avg=Avg("costo_total"))["avg"] or 0

        return Response([
            {"name": "Gastos Totales", "value": float(total)},
            {"name": "Promedio por Reporte", "value": float(promedio)}
        ])


class GastosMensualesView(APIView):
    """Evolución de gastos mensuales"""
    def get(self, request):
        gastos = (
            Reporte.objects
            .annotate(month=TruncMonth("fecha_inicio"))
            .values("month")
            .annotate(total=Sum("costo_total"))
            .order_by("month")
        )
        data = [
            {"month": g["month"].strftime("%Y-%m"), "total": float(g["total"])}
            for g in gastos
        ]
        return Response(data)


# === MOROSIDAD ===
class MorosidadView(APIView):
    """% de cargos pagados vs pendientes"""
    def get(self, request):
        total_cargos = Charge.objects.count()
        pendientes = Charge.objects.filter(status="PENDING").count()
        pagados = Charge.objects.filter(status="PAID").count()

        return Response({
            "total_cargos": total_cargos,
            "pendientes": pendientes,
            "pagados": pagados,
            "tasa_morosidad": round((pendientes / total_cargos * 100), 2) if total_cargos else 0
        })


class CarteraVencidaView(APIView):
    """Monto y propiedades con deuda"""
    def get(self, request):
        vencidos = (
            Charge.objects.filter(status="PENDING", fecha_pago__lt=F("issued_at"))
            .values("propiedad__numero")
            .annotate(deuda=Sum("price_config__base_price"))
        )
        data = [{"propiedad": v["propiedad__numero"], "deuda": float(v["deuda"])} for v in vencidos]
        return Response(data)


# === COMPARATIVOS ===
class IngresosVsGastosView(APIView):
    """Balance global: ingresos - gastos"""
    def get(self, request):
        ingresos = Payment.objects.filter(status="SUCCEEDED").aggregate(total=Sum("amount"))["total"] or 0
        gastos = Reporte.objects.aggregate(total=Sum("costo_total"))["total"] or 0
        balance = ingresos - gastos

        return Response({
            "ingresos": float(ingresos),
            "gastos": float(gastos),
            "balance": float(balance)
        })


class RentabilidadAreasView(APIView):
    """ROI de áreas comunes"""
    def get(self, request):
        areas = AreaComun.objects.all()
        data = []
        for area in areas:
            ingresos = (
                ReservaAreaComun.objects.filter(area=area, estado="APROBADA")
                .count() * float(area.precio)
            )
            # Aquí podrías cruzar con costos de mantenimiento si los vinculas
            data.append({
                "area": area.nombre,
                "ingresos": ingresos,
                "costos": 0,  # Si no tienes gastos específicos por área
                "roi": ingresos  # Aquí luego: ingresos - costos
            })
        return Response(data)
