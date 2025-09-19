# users/views.py
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User, Role, Permission
from .serializers import (
    UserSerializer, RoleSerializer, PermissionSerializer,
    CustomTokenObtainPairSerializer
)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().select_related("role")
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def assign_role(self, request, pk=None):
        user = self.get_object()
        role_id = request.data.get("role_id")
        if not role_id:
            return Response({"error": "role_id es requerido"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            role = Role.objects.get(id=role_id)
        except Role.DoesNotExist:
            return Response({"error": "Rol no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        user.role = role
        user.save(update_fields=["role"])
        return Response({"message": f"Rol '{role.name}' asignado a {user.email}"})

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def remove_role(self, request, pk=None):
        user = self.get_object()
        user.role = None
        user.save(update_fields=["role"])
        return Response({"message": f"Rol removido de {user.email}"})


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all().prefetch_related("permissions")
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]


class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated]
