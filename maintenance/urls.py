from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReporteViewSet, TareaViewSet, MaterialViewSet

router = DefaultRouter()
router.register(r'reportes', ReporteViewSet)
router.register(r'tareas', TareaViewSet)
router.register(r'materiales', MaterialViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
