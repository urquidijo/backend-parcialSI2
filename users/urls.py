from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, CustomTokenObtainPairView, RoleViewSet, PermissionViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'roles', RoleViewSet, basename='roles')          # 👈 agregar
router.register(r'permissions', PermissionViewSet, basename='permissions')  # 👈 agregar

urlpatterns = [
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
]

urlpatterns += router.urls
