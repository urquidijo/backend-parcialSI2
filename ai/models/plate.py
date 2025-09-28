from django.db import models
from django.conf import settings

class Plate(models.Model):
    number = models.CharField(max_length=20, db_index=True)   # no unique si quieres varias por usuario
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="plates")

    class Meta:
        db_table = "ai_plate"
        unique_together = ("number", "user")  # opcional: evita duplicadas en el mismo usuario

    def __str__(self):
        return f"{self.number} -> {self.user_id}"
