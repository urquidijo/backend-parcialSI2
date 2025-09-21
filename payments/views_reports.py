from decimal import Decimal

from django.apps import apps
from django.db import models
from django.db.models import Value, CharField, Q, Exists, OuterRef
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_date

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from payments.models import Payment


def is_admin(user):
    role = getattr(user, "role", None)
    return bool(role and str(getattr(role, "name", "")).lower() in ("administrador", "administrator", "admin"))


def _user_display(first: str | None, last: str | None, email: str | None) -> str:
    f = (first or "").strip()
    l = (last or "").strip()
    full = (f"{f} {l}").strip()
    return full if full else (email or "")


def _property_label_from_charge(charge_obj) -> str:
    if not charge_obj:
        return "-"
    prop = getattr(charge_obj, "propiedad", None)
    if not prop:
        return "-"
    codigo = getattr(prop, "codigo", None)
    if codigo:
        return str(codigo)
    edificio = getattr(prop, "edificio", None)
    numero = getattr(prop, "numero", None)
    if edificio and numero:
        return f"{edificio}-{numero}"
    if numero:
        return str(numero)
    return str(getattr(prop, "id", "-"))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def payments_report(request):
    """
    Reporte de pagos REALIZADOS (SUCCEEDED) SOLO de CARGOS (expensas, multas, etc).
    NO incluye reservas.

    Filtros: q, tipo_id, fecha, desde, hasta, export=csv
    """
    qs = (
        Payment.objects.select_related(
            "user",
            "charge__price_config",
            "charge__propiedad",
        )
        .filter(status=Payment.Status.SUCCEEDED, charge__isnull=False)
    )

    # 🔐 Scope por usuario (dueño o inquilino)
    if not is_admin(request.user):
        # dueños
        Prop = apps.get_model("condominio", "Property")
        names = {f.name for f in Prop._meta.fields}
        owner_q = Q()
        for fname in ("owner", "usuario", "user", "propietario"):
            if fname in names:
                owner_q |= Q(**{f"charge__propiedad__{fname}_id": request.user.id})

        qs = qs.filter(owner_q) if owner_q else qs.none()

        # inquilinos
        try:
            PT = apps.get_model("condominio", "PropertyTenant")
            tnames = {f.name for f in PT._meta.fields}
            user_field = "user" if "user" in tnames else ("usuario" if "usuario" in tnames else None)
            prop_field = "property" if "property" in tnames else ("propiedad" if "propiedad" in tnames else None)
            if user_field and prop_field:
                active_filters = {}
                if "active" in tnames:
                    active_filters["active"] = True
                if "is_active" in tnames:
                    active_filters["is_active"] = True
                if "vigente" in tnames:
                    active_filters["vigente"] = True
                if "end_date" in tnames:
                    active_filters["end_date__isnull"] = True
                if "hasta" in tnames:
                    active_filters["hasta__isnull"] = True

                sub = PT.objects.filter(
                    **{f"{user_field}_id": request.user.id, f"{prop_field}_id": OuterRef("charge__propiedad_id")},
                    **active_filters,
                )
                qs = qs.annotate(_is_tenant=Exists(sub)).filter(owner_q | Q(_is_tenant=True))
        except Exception:
            pass

    # Texto (usuario)
    qtext = (request.query_params.get("q") or "").strip()
    if qtext:
        qs = qs.filter(
            Q(user__first_name__icontains=qtext)
            | Q(user__last_name__icontains=qtext)
            | Q(user__username__icontains=qtext)
            | Q(user__email__icontains=qtext)
        )

    # Por tipo (PriceConfig)
    tipo_id = request.query_params.get("tipo_id")
    if tipo_id:
        qs = qs.filter(charge__price_config_id=tipo_id)

    # Anotaciones
    qs = qs.annotate(
        paid_at_anno=models.F("charge__paid_at"),
        tipo_anno=Coalesce(models.F("charge__price_config__type"), Value("", output_field=CharField())),
        user_first=Coalesce(models.F("user__first_name"), Value("", output_field=CharField())),
        user_last=Coalesce(models.F("user__last_name"), Value("", output_field=CharField())),
        user_email=Coalesce(models.F("user__email"), Value("", output_field=CharField())),
    )

    # Filtros por fecha de pago
    fecha = parse_date(request.query_params.get("fecha") or "")
    desde = parse_date(request.query_params.get("desde") or "")
    hasta = parse_date(request.query_params.get("hasta") or "")
    if fecha:
        qs = qs.filter(paid_at_anno=fecha)
    else:
        if desde and hasta:
            qs = qs.filter(paid_at_anno__range=(desde, hasta))
        elif desde:
            qs = qs.filter(paid_at_anno__gte=desde)
        elif hasta:
            qs = qs.filter(paid_at_anno__lte=hasta)

    # Orden
    qs = qs.order_by("-paid_at_anno", "-id")

    # Serialización manual
    rows = []
    for p in qs:
        tipo = getattr(p, "tipo_anno", "") or ""
        propiedad = _property_label_from_charge(getattr(p, "charge", None))
        residente = _user_display(p.user_first, p.user_last, p.user_email)
        paid_at = p.paid_at_anno.isoformat() if p.paid_at_anno else None
        amount: Decimal = p.amount or Decimal("0.00")
        rows.append(
            {
                "id": p.id,
                "tipo": tipo,
                "propiedad": propiedad,
                "residente": residente,
                "departamento": None,
                "paid_at": paid_at,
                "monto": f"{amount.quantize(Decimal('0.01'))}",
                "moneda": "USD",
                "recibo_url": p.receipt_url or None,
            }
        )

    # CSV
    if (request.query_params.get("export") or "").lower() == "csv":
        import csv
        from django.http import HttpResponse

        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="reporte_pagos.csv"'
        w = csv.writer(resp)
        w.writerow(["Tipo", "Propiedad", "Residente", "Fecha de pago", "Monto", "Moneda", "Comprobante"])
        for r in rows:
            w.writerow([
                r["tipo"],
                r["propiedad"],
                r["residente"],
                r["paid_at"] or "",
                r["monto"],
                r["moneda"] or "",
                r["recibo_url"] or "",
            ])
        return resp

    # Paginación simple
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 20))
    start, end = (page - 1) * page_size, page * page_size
    return Response({"count": len(rows), "results": rows[start:end]}, status=status.HTTP_200_OK)
