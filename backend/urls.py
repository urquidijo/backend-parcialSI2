from django.urls import path, include

urlpatterns = [
    path("api/", include("users.urls")),
    path("api/", include("notices.urls")),
    path("api/", include("commons.urls")),  # 👈 Agregar esto
]
