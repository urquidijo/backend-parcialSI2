# bitacora/urls.py
from django.urls import path
from .views import BitacoraListCreateView

urlpatterns = [
    path("", BitacoraListCreateView.as_view(), name="bitacora-list-create"),
]
