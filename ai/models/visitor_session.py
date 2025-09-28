# ai/models/visitor_session.py
from django.db import models
from django.conf import settings

class VisitorSession(models.Model):
    """
    Una fila por sesión de visitante.
    - Se crea en el login (con foto + similarity).
    - Se cierra en el logout (solo timestamp; no foto).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="visitor_sessions"
    )

    # tiempos
    login_at  = models.DateTimeField(auto_now_add=True)
    logout_at = models.DateTimeField(null=True, blank=True)  # queda NULL hasta que salga

    # metadata del ingreso
    similarity = models.FloatField(default=0.0)
    s3_key     = models.CharField(max_length=512, blank=True, default="")

    # por si quieres filtrar en admin o APIs
    event_type = models.CharField(max_length=16, default="session")

    class Meta:
        db_table = "ai_visitor_session"
        indexes = [
            models.Index(fields=["user", "login_at"]),
            models.Index(fields=["user", "logout_at"]),
        ]

    def __str__(self):
        return f"Session<{self.pk}> user={self.user_id} {self.login_at:%Y-%m-%d %H:%M} -> {self.logout_at or '...'}"
