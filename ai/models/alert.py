from django.db import models

class Alert(models.Model):
    TYPE_CHOICES = [
        ("dog_loose", "Perro suelto"),
        ("dog_waste", "Perro haciendo necesidades"),
        ("bad_parking", "Vehículo mal estacionado"),
    ]
    type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    camera_id = models.CharField(max_length=64, blank=True, null=True)
    s3_video_key = models.CharField(max_length=512)
    s3_image_key = models.CharField(max_length=512, blank=True, null=True)
    timestamp_ms = models.BigIntegerField()  # milisegundos dentro del video
    confidence = models.FloatField(default=0.0)
    extra = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_alerts"
        indexes = [models.Index(fields=["type", "created_at"])]

    def __str__(self):
        return f"{self.type} @ {self.timestamp_ms}ms"
