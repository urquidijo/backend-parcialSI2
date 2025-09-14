from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.dateparse import parse_date

from .models import AreaComun, ReservaAreaComun
from .serializers import AreaComunSerializer, ReservaAreaComunSerializer


def is_admin(user):
    role = getattr(user, "role", None)
    return bool(role and role.name.lower() in ("administrador", "administrator", "admin"))


class AreaComunViewSet(viewsets.ModelViewSet):
    queryset = AreaComun.objects.all().order_by("nombre")
    serializer_class = AreaComunSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        if not is_admin(self.request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Solo administradores pueden crear áreas.")
        serializer.save()

    def perform_update(self, serializer):
        if not is_admin(self.request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Solo administradores pueden modificar áreas.")
        serializer.save()

    def perform_destroy(self, instance):
        if not is_admin(self.request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Solo administradores pueden eliminar áreas.")
        instance.delete()


class ReservaAreaComunViewSet(viewsets.ModelViewSet):
    # ❌ antes: order_by("-fecha_inicio")
    queryset = ReservaAreaComun.objects.select_related("area", "usuario").all().order_by("-fecha_reserva", "-hora_inicio")
    serializer_class = ReservaAreaComunSerializer
    permission_classes = [permissions.IsAuthenticated]

    # por defecto, list() devuelve MIS reservas
    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            return qs.filter(usuario=self.request.user)
        return qs

    @action(detail=False, methods=["get"], url_path="occupied")
    def occupied(self, request):
        """
        GET /api/reservations/occupied/?area=<ID>&date=YYYY-MM-DD
        (Opcional) soporta rango: ?from=YYYY-MM-DD&to=YYYY-MM-DD
        Devuelve bloques ocupados (PENDIENTE o APROBADA) por día.
        """
        area_id = request.query_params.get("area")
        if not area_id:
            return Response({"detail": "Parámetro ?area requerido"}, status=400)

        date_str = request.query_params.get("date")
        desde_str = request.query_params.get("from") or request.query_params.get("desde")
        hasta_str = request.query_params.get("to") or request.query_params.get("hasta")

        qs = ReservaAreaComun.objects.filter(area_id=area_id, estado__in=["PENDIENTE", "APROBADA"])

        if date_str:
            d = parse_date(date_str)
            if not d:
                return Response({"detail": "date inválido (YYYY-MM-DD)"}, status=400)
            qs = qs.filter(fecha_reserva=d)
        else:
            d1 = parse_date(desde_str) if desde_str else None
            d2 = parse_date(hasta_str) if hasta_str else None
