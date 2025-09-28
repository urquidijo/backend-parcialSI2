# ai/urls.py
from django.urls import path
from .views import FaceDebugView, FaceEnrollView, FaceLoginView, FaceStatusView, FaceRevokeView

urlpatterns = [
    path("face/enroll/", FaceEnrollView.as_view(), name="ai-face-enroll"),
    path("face/login/",  FaceLoginView.as_view(),  name="ai-face-login"),
    path("face/status/<int:user_id>/", FaceStatusView.as_view(), name="ai-face-status"),
    path("face/revoke/", FaceRevokeView.as_view(), name="ai-face-revoke"),
    path("face/debug/", FaceDebugView.as_view()),    
]
