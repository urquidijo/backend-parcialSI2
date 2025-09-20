from django.db import models
from users.models import User

class Bitacora(models.Model):
    ESTADO_CHOICES = [
        ("exitoso", "Exitoso"),
        ("fallido", "Fallido"),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bitacoras")
    ip = models.GenericIPAddressField()  # se guardará el IP real
    fecha_entrada = models.DateField(auto_now_add=True)
    hora_entrada = models.TimeField(auto_now_add=True)
    acciones = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES)

    class Meta:
        db_table = "bitacora"
        ordering = ["-fecha_entrada", "-hora_entrada"]

    def __str__(self):
        return f"{self.usuario.email} - {self.acciones} ({self.estado})"
