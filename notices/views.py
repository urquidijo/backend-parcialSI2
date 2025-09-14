from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Notice
from .serializers import NoticeSerializer

class IsOwnerOrAdminOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Lectura pública
        if request.method in permissions.SAFE_METHODS:
            return True
        # El creador siempre puede modificar/eliminar
        if obj.created_by == request.user:
            return True
        # Si es admin por rol
        if hasattr(request.user, "role") and request.user.role and request.user.role.name == "Admin":
            return True
        return False


class NoticeViewSet(viewsets.ModelViewSet):
    queryset = Notice.objects.all()
    serializer_class = NoticeSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdminOrReadOnly]

    def perform_create(self, serializer):
        if self.request.user.is_anonymous:
            raise PermissionDenied("Debes iniciar sesión para crear un aviso.")
        serializer.save(created_by=self.request.user)
