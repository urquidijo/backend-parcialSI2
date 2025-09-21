from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q, F
from django.utils import timezone
from users.models import User


class AreaComun(models.Model):
    ESTADOS = [
        ("DISPONIBLE", "Disponible"),
        ("MANTENIMIENTO", "Mantenimiento"),
        ("CERRADO", "Cerrado"),
    ]
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    capacidad = models.PositiveIntegerField(default=0)
    ubicacion = models.CharField(max_length=150, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="DISPONIBLE")
    horario_apertura = models.TimeField()
    horario_cierre = models.TimeField()
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = "areacomun"
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(
                check=Q(horario_apertura__lt=F("horario_cierre")),
                name="area_horario_apertura_menor_cierre",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.estado})"


class ReservaAreaComun(models.Model):
    ESTADOS = [
        ("PENDIENTE", "Pendiente"),
        ("APROBADA", "Aprobada"),
        ("CANCELADA", "Cancelada"),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reservas_areas")
    area = models.ForeignKey(AreaComun, on_delete=models.CASCADE, related_name="reservas")
    fecha_reserva = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    estado = models.CharField(max_length=10, choices=ESTADOS, default="PENDIENTE")

    # ✅ Nueva: fecha en la que la reserva quedó en APROBADA (solo fecha)
    approved_at = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "reserva_areacomun"
        ordering = ["-fecha_reserva", "hora_inicio"]
        constraints = [
            models.CheckConstraint(
                check=Q(hora_inicio__lt=F("hora_fin")),
                name="res_hora_inicio_menor_fin",
            ),
        ]

    def clean(self):
        if self.area.estado != "DISPONIBLE":
            raise ValidationError("El área no está disponible para reservas.")
        if not (self.area.horario_apertura <= self.hora_inicio < self.hora_fin <= self.area.horario_cierre):
            raise ValidationError("La reserva debe estar dentro del horario del área.")

        qs = ReservaAreaComun.objects.filter(
            area=self.area,
            fecha_reserva=self.fecha_reserva,
            estado__in=["PENDIENTE", "APROBADA"],
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.filter(hora_inicio__lt=self.hora_fin, hora_fin__gt=self.hora_inicio).exists():
            raise ValidationError("Ya existe una reserva que se superpone en ese horario.")

    def save(self, *args, **kwargs):
        # Detectar transición a APROBADA y fijar fecha (solo una vez)
        today = timezone.localdate()
        if self.pk:
            orig = type(self).objects.only("estado", "approved_at").get(pk=self.pk)
            if orig.estado != "APROBADA" and self.estado == "APROBADA" and not self.approved_at:
                self.approved_at = today
        else:
            # Si se crea ya aprobada, guardar la fecha de aprobación
            if self.estado == "APROBADA" and not self.approved_at:
                self.approved_at = today

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.area.nombre} - {self.usuario.email} ({self.fecha_reserva} {self.hora_inicio}-{self.hora_fin})"
