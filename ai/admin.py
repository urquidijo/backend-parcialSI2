from django.contrib import admin
from ai.models import UserFace

@admin.register(UserFace)
class UserFaceAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "external_image_id", "face_id", "status", "created_at")
    search_fields = ("external_image_id", "face_id", "user__email")
    list_filter = ("status",)
