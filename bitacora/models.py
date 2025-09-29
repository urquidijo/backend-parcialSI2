from django.db import models
from django.utils import timezone
from zoneinfo import ZoneInfo  # estándar en Python 3.9+
from users.models import User


class Bitacora(models.Model):
    ESTADO_CHOICES = [
        ("exitoso", "Exitoso"),
        ("fallido", "Fallido"),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bitacoras")
    ip = models.GenericIPAddressField()
    fecha_entrada = models.DateField()
    hora_entrada = models.TimeField()
    acciones = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES)

    def save(self, *args, **kwargs):
        if not self.id:  # solo al crear
            now = timezone.now().astimezone(ZoneInfo("America/La_Paz"))
            self.fecha_entrada = now.date()
            self.hora_entrada = now.time()
        super().save(*args, **kwargs)

    class Meta:
        db_table = "bitacora"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.usuario.email} - {self.acciones} ({self.estado})"
