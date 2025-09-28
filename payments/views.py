# backend/payments/views.py
from decimal import Decimal, ROUND_HALF_UP
import stripe

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from commons.models import ReservaAreaComun
from .models import Payment, PriceConfig, Charge
from .serializers import PaymentSerializer, PriceConfigSerializer, ChargeSerializer

# 👇 tu modelo de casa
from condominio.models import Property

from django.db.models import Q
from condominio.models import Property, PropertyTenant
from .models import Charge  # tu modelo de cargos
# =========================
# Stripe & URLs
# =========================
stripe.api_key = settings.STRIPE_SECRET_KEY
SUCCESS_URL = getattr(settings, "FRONTEND_SUCCESS_URL", "http://localhost:5173/reservas?success=true")
CANCEL_URL = getattr(settings, "FRONTEND_CANCEL_URL", "http://localhost:5173/reservas?canceled=true")
DEFAULT_CURRENCY = getattr(settings, "PAYMENTS_DEFAULT_CURRENCY", "usd").lower()


# =========================
# Helpers de Stripe
# =========================
def _extract_receipt_from_session(session_id: str):
    try:
        session = stripe.checkout.Session.retrieve(
            session_id, expand=["payment_intent.latest_charge"]
        )
        pi = session.get("payment_intent")
        pi_id = pi.get("id") if isinstance(pi, dict) else None

        receipt = None
        if isinstance(pi, dict):
            latest = pi.get("latest_charge")
            if isinstance(latest, dict):
                receipt = latest.get("receipt_url")
            elif isinstance(latest, str):
                ch = stripe.Charge.retrieve(latest)
                receipt = ch.get("receipt_url")
        return pi_id, receipt
    except Exception:
        return None, None


def _extract_receipt_from_intent(pi_id: str):
    try:
        pi = stripe.PaymentIntent.retrieve(pi_id, expand=["latest_charge"])
        latest = pi.get("latest_charge")
        if isinstance(latest, dict):
            return latest.get("receipt_url")
        if isinstance(latest, str):
            ch = stripe.Charge.retrieve(latest)
            return ch.get("receipt_url")
    except Exception:
        pass
    try:
        charges = stripe.Charge.list(payment_intent=pi_id, limit=1)
        data = charges.get("data", [])
        if data:
            return data[0].get("receipt_url")
    except Exception:
        pass
    return None


def _mark_paid(payment: Payment, pi_id: str | None, receipt_url: str | None):
    if pi_id and not payment.stripe_payment_intent_id:
        payment.stripe_payment_intent_id = pi_id
    payment.status = Payment.Status.SUCCEEDED
    if receipt_url:
        payment.receipt_url = receipt_url
    payment.save(update_fields=["status", "receipt_url", "stripe_payment_intent_id"])

    # Actualiza destino
    if payment.reservation_id:
        res = payment.reservation
        if res.estado != "APROBADA":
            res.estado = "APROBADA"
        if not res.approved_at:
            res.approved_at = timezone.localdate()
        res.save(update_fields=["estado", "approved_at"])

    if payment.charge_id:
        ch = payment.charge
        if ch.status != Charge.Status.PAID:
            ch.status = Charge.Status.PAID
        if not ch.paid_at:
            ch.paid_at = timezone.localdate()
        ch.save(update_fields=["status", "paid_at"])


# =========================
# Permisos
# =========================
def is_admin(user):
    role = getattr(user, "role", None)
    return bool(role and str(getattr(role, "name", "")).lower() in ("administrador", "administrator", "admin"))


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and is_admin(request.user)


# =========================
# Catalogo de precios
# =========================
class PriceConfigViewSet(viewsets.ModelViewSet):
    queryset = PriceConfig.objects.all().order_by("type")
    serializer_class = PriceConfigSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        active = self.request.query_params.get("active")
        if q:
            qs = qs.filter(Q(type__icontains=q))
        if active in ("0", "1"):
            qs = qs.filter(active=(active == "1"))
        return qs

    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        if not is_admin(request.user):
            return Response({"detail": "Solo administradores."}, status=status.HTTP_403_FORBIDDEN)
        obj = self.get_object()
        active = str(request.data.get("active", "")).lower()
        if active in ("1", "true", "t", "yes", "y"):
            obj.active = True
        elif active in ("0", "false", "f", "no", "n"):
            obj.active = False
        else:
            return Response({"detail": "Valor 'active' inválido."}, status=400)
        obj.save(update_fields=["active"])
        return Response(PriceConfigSerializer(obj).data)


# =========================
# Cargos / Multas
# =========================
class ChargeViewSet(viewsets.ModelViewSet):
    """
    VISIBILIDAD:
      - Admin: ve todos los cargos.
      - Copropietario: solo cargos de sus propiedades (Property.owner).
      - Inquilino: solo cargos de propiedades donde figura en M2M Property.tenants.
    """
    queryset = Charge.objects.select_related("price_config", "propiedad").all()
    serializer_class = ChargeSerializer
    permission_classes = [permissions.IsAuthenticated]




    def get_queryset(self):
        user = self.request.user
        qs = Charge.objects.select_related("price_config", "propiedad")  # "propiedad" es la FK a property

        # 1) Admin ve todo
        if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False) or getattr(user, "role_id", None) == 1:
            return qs

        # 2) Propiedades donde es dueño
        owned_ids = Property.objects.filter(owner=user).values_list("id", flat=True)

        # 3) Propiedades donde es inquilino (tabla puente que mostraste)
        tenant_ids = PropertyTenant.objects.filter(user=user).values_list("property_id", flat=True)

        # 4) Unimos ambos conjuntos
        my_prop_ids = list(set(owned_ids).union(set(tenant_ids)))

        # Si no está vinculado a ninguna, no ve nada
        if not my_prop_ids:
            return qs.none()

        # 5) Filtramos por la FK real del modelo Charge → `propiedad`
        return qs.filter(propiedad_id__in=my_prop_ids)

    def perform_create(self, serializer):
        if not is_admin(self.request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Solo administradores pueden crear cargos.")
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        if not is_admin(self.request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Solo administradores pueden modificar cargos.")
        serializer.save()

    def perform_destroy(self, instance):
        if not is_admin(self.request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Solo administradores pueden eliminar cargos.")
        instance.delete()


# =========================
# Stripe Checkout (reserva o cargo)
# =========================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    """
    Body JSON:
      - reservation_id OR charge_id (exactamente uno)
    """
    reservation_id = request.data.get("reservation_id")
    charge_id = request.data.get("charge_id")

    if bool(reservation_id) == bool(charge_id):
        return Response({"error": "Debes enviar exactamente uno: reservation_id o charge_id."}, status=400)

    if reservation_id:
        reserva = get_object_or_404(
            ReservaAreaComun.objects.select_related("area"),
            pk=reservation_id,
            usuario=request.user,
        )
        amount_dec = Decimal(reserva.area.precio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        target_kwargs = {"reservation": reserva}
        product_name = f"Reserva Área - {reserva.area.nombre}"
    else:
        cargo = get_object_or_404(Charge.objects.select_related("price_config", "propiedad"), pk=charge_id)

        # Seguridad: si NO es admin, solo puede pagar cargos de sus propiedades (owner o tenants)
        if not is_admin(request.user):
            ok = Property.objects.filter(
                Q(pk=cargo.propiedad_id) & (Q(owner=request.user) | Q(tenants=request.user))
            ).exists()
            if not ok:
                return Response({"detail": "No tienes acceso a este cargo."}, status=403)

        amount_dec = Decimal(cargo.amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        target_kwargs = {"charge": cargo}
        product_name = f"Cargo - {cargo.price_config.type}"

    currency = DEFAULT_CURRENCY

    payment, _ = Payment.objects.update_or_create(
        user=request.user,
        **target_kwargs,
        defaults={
            "amount": amount_dec,
            "status": Payment.Status.PENDING,
        },
    )

    unit_amount = int((amount_dec * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": currency,
                "product_data": {"name": product_name},
                "unit_amount": unit_amount,
            },
            "quantity": 1,
        }],
        mode="payment",
        customer_email=getattr(request.user, "email", None),
        success_url=SUCCESS_URL,
        cancel_url=CANCEL_URL,
        metadata={
            "payment_id": str(payment.id),
            "user_id": str(request.user.id),
            "kind": "reservation" if reservation_id else "charge",
            "reservation_id": str(reservation_id or ""),
            "charge_id": str(charge_id or ""),
        },
    )

    payment.stripe_session_id = session.id
    payment.save(update_fields=["stripe_session_id"])

    return Response({"sessionId": session.id, "amount": f"{amount_dec:.2f}", "currency": currency.upper()}, status=200)


# =========================
# Webhook Stripe
# =========================
@api_view(["POST"])
@permission_classes([AllowAny])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=sig_header, secret=settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        return Response({"error": f"Invalid signature: {e}"}, status=400)

    etype = event.get("type")
    data = event.get("data", {}).get("object", {})

    if etype == "checkout.session.completed":
        session_id = data.get("id")
        payment = None

        meta = data.get("metadata") or {}
        pid_meta = meta.get("payment_id")
        if pid_meta:
            payment = Payment.objects.filter(id=pid_meta).select_related("reservation", "charge").first()
        if not payment and session_id:
            payment = Payment.objects.filter(stripe_session_id=session_id).select_related("reservation", "charge").first()

        pi_id, receipt = (None, None)
        if session_id:
            pi_id, receipt = _extract_receipt_from_session(session_id)
        if not receipt and pi_id:
            receipt = _extract_receipt_from_intent(pi_id)

        if payment:
            _mark_paid(payment, pi_id, receipt)
        return Response({"ok": True}, status=200)

    if etype == "payment_intent.succeeded":
        pi_id = data.get("id")
        payment = Payment.objects.filter(stripe_payment_intent_id=pi_id).select_related("reservation", "charge").first()
        if not payment:
            session_id = data.get("checkout_session")
            if session_id:
                payment = Payment.objects.filter(stripe_session_id=session_id).select_related("reservation", "charge").first()

        receipt = _extract_receipt_from_intent(pi_id) if pi_id else None
        if payment:
            _mark_paid(payment, pi_id, receipt)
        return Response({"ok": True}, status=200)

    if etype == "payment_intent.payment_failed":
        pi_id = data.get("id")
        Payment.objects.filter(stripe_payment_intent_id=pi_id).update(status=Payment.Status.FAILED)
        return Response({"ok": True}, status=200)

    return Response({"ignored": etype}, status=200)


# =========================
# Conciliar manualmente (solo admin)
# =========================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reconcile_payment(request, pk: int):
    if not is_admin(request.user):
        return Response({"detail": "Solo administradores."}, status=status.HTTP_403_FORBIDDEN)

    payment = get_object_or_404(Payment.objects.select_related("reservation", "charge"), pk=pk)

    if payment.status == Payment.Status.SUCCEEDED:
        return Response({"detail": "El pago ya está conciliado."})

    _mark_paid(payment, payment.stripe_payment_intent_id, payment.receipt_url)
    return Response({"ok": True})
