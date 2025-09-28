from django.contrib import admin
from ai.models import UserFace

@admin.register(UserFace)
class UserFaceAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "external_image_id", "face_id", "status", "created_at")
    search_fields = ("external_image_id", "face_id", "user__email")
    list_filter = ("status",)


from django.contrib import admin
from ai.models.alert import Alert

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("id","type","timestamp_ms","camera_id","created_at")
    search_fields = ("type","camera_id","s3_video_key","s3_image_key")
    list_filter = ("type",)



from django.contrib import admin
from ai.models.visitor_session import VisitorSession

@admin.register(VisitorSession)
class VisitorSessionAdmin(admin.ModelAdmin):
    list_display  = ("id", "user", "login_at", "logout_at", "similarity", "s3_key", "event_type")
    list_filter   = ("event_type",)
    search_fields = ("user__email", "user__first_name", "user__last_name", "s3_key")