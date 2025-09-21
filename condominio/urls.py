# condominio/urls.py
from rest_framework.routers import DefaultRouter
from .views import PropertyViewSet

router = DefaultRouter()
router.register(r'properties', PropertyViewSet, basename='properties')

urlpatterns = router.urls
