from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import User, Role, Permission
from .serializers import UserSerializer, CustomTokenObtainPairSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    # Asignar rol
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def assign_role(self, request, pk=None):
        user = self.get_object()
        role_id = request.data.get("role_id")
        if not role_id:
            return Response({"error": "role_id es requerido"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            role = Role.objects.get(id=role_id)
            user.role = role
            user.save()
            return Response({"message": f"Rol '{role.name}' asignado a {user.email}"}, status=status.HTTP_200_OK)
        except Role.DoesNotExist:
            return Response({"error": "Rol no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    # Quitar rol
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def remove_role(self, request, pk=None):
        user = self.get_object()
        user.role = None
        user.save()
        return Response({"message": f"Rol removido de {user.email}"}, status=status.HTTP_200_OK)

    # Agregar permiso extra
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def add_permission(self, request, pk=None):
        user = self.get_object()
        perm_id = request.data.get("permission_id")
        if not perm_id:
            return Response({"error": "permission_id es requerido"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            perm = Permission.objects.get(id=perm_id)
            user.extra_permissions.add(perm)
            return Response({"message": f"Permiso '{perm.code}' agregado a {user.email}"}, status=status.HTTP_200_OK)
        except Permission.DoesNotExist:
            return Response({"error": "Permiso no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    # Quitar permiso extra
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def remove_permission(self, request, pk=None):
        user = self.get_object()
        perm_id = request.data.get("permission_id")
        if not perm_id:
            return Response({"error": "permission_id es requerido"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            perm = Permission.objects.get(id=perm_id)
            user.extra_permissions.remove(perm)
            return Response({"message": f"Permiso '{perm.code}' removido de {user.email}"}, status=status.HTTP_200_OK)
        except Permission.DoesNotExist:
            return Response({"error": "Permiso no encontrado"}, status=status.HTTP_404_NOT_FOUND)



from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import User, Role, Permission
from .serializers import UserSerializer, RoleSerializer, PermissionSerializer

class RoleViewSet(viewsets.ModelViewSet):   # 👈
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]

class PermissionViewSet(viewsets.ModelViewSet):   # 👈
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated]

