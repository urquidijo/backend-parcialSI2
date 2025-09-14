from django.db import models
from users.models import User

class Notice(models.Model):
    class Priority(models.TextChoices):
        ALTA = "ALTA", "Alta"
        MEDIA = "MEDIA", "Media"
        BAJA = "BAJA", "Baja"

    title = models.CharField(max_length=150, verbose_name="Título")
    content = models.TextField(verbose_name="Contenido")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notices")
    created_at = models.DateTimeField(auto_now_add=True)
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIA,
        verbose_name="Prioridad"
    )

    class Meta:
        db_table = "avisos"   # 👈 Nombre de la tabla en la BD
        ordering = ["-created_at"]
        verbose_name = "Aviso"
        verbose_name_plural = "Avisos"

    def __str__(self):
        return f"{self.title} ({self.priority})"
