from django.db.models import OuterRef, Subquery, Value, CharField, DecimalField, Q, DateField, IntegerField
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from commons.models import ReservaAreaComun
from payments.models import Payment
from commons.serializers import UsageReportRowSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def usage_report(request):
    """
    Reporte de uso de instalaciones.
    - Muestra SOLO reservas aprobadas y pagadas (Payment.status=SUCCEEDED).
    - Orden: último pago (Payment.id DESC), luego approved_at DESC.
    - CSV y JSON devuelven columnas usadas por el frontend.
    Filtros: q, area_id, fecha (approved_at), desde, hasta, export=csv
    """
    qs = ReservaAreaComun.objects.select_related("area", "usuario")

    # Texto
    q = request.query_params.get("q")
    if q:
        qs = qs.filter(
            Q(usuario__first_name__icontains=q)
            | Q(usuario__last_name__icontains=q)
            | Q(usuario__username__icontains=q)
            | Q(usuario__email__icontains=q)
        )

    # Instalación
    area_id = request.query_params.get("area_id")
    if area_id:
        qs = qs.filter(area_id=area_id)

    # Subquery al último Payment de la reserva
    pay_qs = Payment.objects.filter(reservation_id=OuterRef("pk")).order_by("-id")

    qs = qs.annotate(
        pago_monto=Coalesce(
            Subquery(pay_qs.values("amount")[:1]),
            Value(0, output_field=DecimalField(max_digits=10, decimal_places=2)),
        ),
        pago_estado=Coalesce(
            Subquery(pay_qs.values("status")[:1]),
            Value("PENDING", output_field=CharField()),
        ),
        pago_recibo=Coalesce(
            Subquery(pay_qs.values("receipt_url")[:1]),
            Value("", output_field=CharField()),
        ),
        # usamos id del último pago para ordenar (ya no existe created_at)
        pago_id=Coalesce(
            Subquery(pay_qs.values("id")[:1]),
            Value(0, output_field=IntegerField()),
        ),
    )

    # SOLO aprobadas y pagadas
    qs = qs.filter(approved_at__isnull=False, pago_estado="SUCCEEDED")

    # Filtro por fecha de aprobación
    fecha = request.query_params.get("fecha")
    if fecha:
        d = parse_date(fecha)
        if d:
            qs = qs.filter(approved_at=d)
    else:
        desde = parse_date(request.query_params.get("desde") or "")
        hasta = parse_date(request.query_params.get("hasta") or "")
        if desde and hasta:
            qs = qs.filter(approved_at__range=(desde, hasta))
        elif desde:
            qs = qs.filter(approved_at__gte=desde)
        elif hasta:
            qs = qs.filter(approved_at__lte=hasta)

    # Orden final
    qs = qs.order_by("-pago_id", "-approved_at", "-fecha_reserva", "-hora_inicio", "-id")

    # Selección de columnas
    rows = qs.values(
        "id",
        "area__nombre",
        "usuario__first_name",
        "usuario__last_name",
        "usuario__email",
        "approved_at",
        "hora_inicio",
        "hora_fin",
        "area__precio",
        "pago_monto",
        "pago_estado",
        "pago_recibo",
    )

    # Normalización para el serializer
    data = []
    for r in rows:
        residente = (r.get("usuario__first_name") or "").strip()
        last = (r.get("usuario__last_name") or "").strip()
        if last:
            residente = (residente + " " + last).strip()
        if not residente:
            residente = r.get("usuario__email") or ""
        data.append(
            {
                "id": r["id"],
                "area_nombre": r["area__nombre"],
                "residente": residente,
                "departamento": None,
                "fecha_aprobada": r["approved_at"],
                "hora_inicio": r["hora_inicio"],
                "hora_fin": r["hora_fin"],
                "precio": r["area__precio"],
                "pago_monto": r["pago_monto"],
                "pago_estado": r["pago_estado"],
                "pago_recibo": r["pago_recibo"],
            }
        )

    # Export CSV
    if request.query_params.get("export") == "csv":
        import csv
        from django.http import HttpResponse

        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="reporte_uso_instalaciones.csv"'
        writer = csv.writer(resp)
        writer.writerow(
            ["Instalación", "Residente", "Departamento", "Fecha Aprobada", "Horario", "Precio", "Monto"]
        )
        for row in data:
            horario = f'{row["hora_inicio"]}-{row["hora_fin"]}'
            writer.writerow(
                [
                    row["area_nombre"],
                    row["residente"],
                    row["departamento"] or "",
                    row["fecha_aprobada"] or "",
                    horario,
                    row["precio"],
                    row["pago_monto"],
                ]
            )
        return resp

    # Paginación simple
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 20))
    start, end = (page - 1) * page_size, page * page_size
    total = len(data)

    serializer = UsageReportRowSerializer(data=data[start:end], many=True)
    serializer.is_valid(raise_exception=True)
    return Response({"count": total, "results": serializer.validated_data}, status=status.HTTP_200_OK)
