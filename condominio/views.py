from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Property, PropertyTenant
from .serializers import PropertySerializer, PropertyTenantSerializer
from users.models import User


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.all().select_related("owner")
    serializer_class = PropertySerializer
    permission_classes = [IsAuthenticated]

    filterset_fields = ["edificio", "estado"]
    # ❌ quita campos legacy; ✅ permite buscar por dueño
    search_fields = ["numero", "owner__email", "owner__first_name", "owner__last_name"]
    ordering_fields = ["numero", "edificio"]
    ordering = ["edificio", "numero"]

    @action(detail=False, methods=["get"])
    def next_number(self, request):
        edificio = (request.query_params.get("edificio") or "").upper().strip()
        if not edificio:
            return Response({"error": "Falta parámetro 'edificio'"}, status=400)

        existing = Property.objects.filter(edificio=edificio).values_list("numero", flat=True)
        existing_nums = set()
        for num in existing:
            try:
                existing_nums.add(int(num.split("-")[1]))
            except Exception:
                continue
        next_n = 101
        while next_n in existing_nums:
            next_n += 1
        return Response({"sugerido": f"{edificio}-{next_n}"})

    @action(detail=True, methods=["get"])
    def tenants(self, request, pk=None):
        prop = self.get_object()
        ser = PropertyTenantSerializer(prop.tenants.select_related("user"), many=True)
        return Response(ser.data)

    @action(detail=True, methods=["post"])
    def add_tenant(self, request, pk=None):
        prop = self.get_object()
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"error": "user_id es requerido"}, status=400)
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": "Usuario no existe"}, status=404)

        obj, created = PropertyTenant.objects.get_or_create(property=prop, user=user)

        # si hay inquilino -> ocupada
        if prop.estado != "ocupada":
            prop.estado = "ocupada"
            prop.save(update_fields=["estado"])

        ser = PropertyTenantSerializer(obj)
        return Response(ser.data, status=201 if created else 200)

    @action(detail=True, methods=["post"])
    def remove_tenant(self, request, pk=None):
        prop = self.get_object()
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"error": "user_id es requerido"}, status=400)

        PropertyTenant.objects.filter(property=prop, user_id=user_id).delete()

        # si no quedan inquilinos ni dueño -> disponible
        if not prop.tenants.exists() and not prop.owner_id:
            prop.estado = "disponible"
            prop.save(update_fields=["estado"])
        return Response(status=204)
