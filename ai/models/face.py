# ai/models/face.py
from django.db import models
from django.conf import settings

class UserFace(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="faces")
    external_image_id = models.CharField(max_length=128, db_index=True)  # ej: str(user.id)
    face_id = models.CharField(max_length=128, blank=True, null=True)    # FaceId de Rekognition
    collection_id = models.CharField(max_length=128)
    s3_key = models.CharField(max_length=512, blank=True, null=True)     # faces/enroll/xxxx.jpg
    status = models.CharField(max_length=32, default="registered")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_userface"
        unique_together = ("user", "collection_id")

    def __str__(self):
        return f"{self.user_id} -> {self.external_image_id} ({self.collection_id})"
