from django.urls import path, include

urlpatterns = [
    path("api/", include("users.urls")),
    path("api/", include("notices.urls")),
    path("api/", include("commons.urls")),  # 👈 Agregar esto
    path("api/", include("condominio.urls")),  # 👈 propiedades
    path("api/payments/", include("payments.urls")), 
    path('api/maintenance/', include('maintenance.urls')),
    path("api/", include("bitacora.urls")),

]
