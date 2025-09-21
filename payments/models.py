from django.db import models
from django.conf import settings
from django.db.models import Q

UserModel = settings.AUTH_USER_MODEL


# =========================
# Catálogo de precios (sin description)
# =========================
class PriceConfig(models.Model):
    type = models.CharField(max_length=120, unique=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "payments_priceconfig"
        ordering = ["type"]

    def __str__(self):
        return f"{self.type} ({self.base_price})"


# =========================
# Cargo/Multa por propiedad
# =========================
class Charge(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        CANCELED = "CANCELED", "Canceled"
        OVERDUE = "OVERDUE", "Overdue"

    # ¡OJO!: el campo se llama 'propiedad', no 'property'
    propiedad = models.ForeignKey(
        "condominio.Property",
        on_delete=models.CASCADE,
        related_name="charges",
    )

    price_config = models.ForeignKey(
        PriceConfig, on_delete=models.PROTECT, related_name="charges"
    )

    fecha_pago = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    issued_at = models.DateField(auto_now_add=True)
    paid_at = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "payments_charge"
        ordering = ["-issued_at", "-fecha_pago", "-id"]

    def __str__(self):
        return f"Charge#{self.pk} ({self.price_config.type})"

    @property
    def amount(self):
        return self.price_config.base_price


# =========================
# Payment (reserva o cargo)
# =========================
class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, related_name="payments")

    # Uno u otro: reserva o cargo (mutuamente excluyentes)
    reservation = models.OneToOneField(
        "commons.ReservaAreaComun",
        on_delete=models.CASCADE,
        related_name="payment",
        null=True, blank=True,
    )
    charge = models.OneToOneField(
        Charge,
        on_delete=models.CASCADE,
        related_name="payment",
        null=True, blank=True,
    )

    stripe_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True, null=True, blank=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    receipt_url = models.URLField(null=True, blank=True)

    class Meta:
        db_table = "payments_payment"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["user"]),
        ]
        constraints = [
            models.CheckConstraint(
                name="payment_target_exactly_one",
                check=(
                    (Q(reservation__isnull=False) & Q(charge__isnull=True))
                    | (Q(reservation__isnull=True) & Q(charge__isnull=False))
                ),
            )
        ]

    def __str__(self):
        target = f"reserva={self.reservation_id}" if self.reservation_id else f"cargo={self.charge_id}"
        return f"Payment({target}, {self.status})"
