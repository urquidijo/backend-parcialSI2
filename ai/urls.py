# ai/urls.py
from django.urls import path

from .views.face_views import (
    FaceDebugView, FaceEnrollView, FaceLoginView,
    FaceStatusView, FaceRevokeView,
)
from .views.plate_views import PlateDetectView, PlateAssignView, PlateVerifyView
from .views.video_views import VideoUploadAndProcessView, AlertListView

from .views.visitor_auth_views import (
    VisitorRegisterView, VisitorLoginView,
    VisitorLogoutView, VisitorLastStatusView,
)
from .views.visitor_session_views import (           # 👈 IMPORTA LAS NUEVAS
    VisitorSessionListView, VisitorSessionStatsView
)

urlpatterns = [
    # facial
    path("face/enroll/", FaceEnrollView.as_view(), name="ai-face-enroll"),
    path("face/login/",  FaceLoginView.as_view(),  name="ai-face-login"),
    path("face/status/<int:user_id>/", FaceStatusView.as_view(), name="ai-face-status"),
    path("face/revoke/", FaceRevokeView.as_view(), name="ai-face-revoke"),
    path("face/debug/",  FaceDebugView.as_view(),  name="ai-face-debug"),

    # placas
    path("plates/detect/",  PlateDetectView.as_view(), name="ai-plate-detect"),
    path("plates/assign/",  PlateAssignView.as_view(), name="ai-plate-assign"),
    path("plates/verify/",  PlateVerifyView.as_view(), name="ai-plate-verify"),
    path("video/upload-and-process/", VideoUploadAndProcessView.as_view(), name="ai-video-upload-process"),
    path("alerts/", AlertListView.as_view(), name="ai-alerts"),

    # visitantes: auth + estado
    path("visitor/register/",    VisitorRegisterView.as_view(),    name="ai-visitor-register"),
    path("visitor/login/",       VisitorLoginView.as_view(),       name="ai-visitor-login"),
    path("visitor/logout/",      VisitorLogoutView.as_view(),      name="ai-visitor-logout"),
    path("visitor/last-status/<int:user_id>/", VisitorLastStatusView.as_view(), name="ai-visitor-last-status"),

    # visitantes: **LISTADO & STATS**  ✅
 path("visitor/sessions/",       VisitorSessionListView.as_view(), name="ai-visitor-sessions"),
]
