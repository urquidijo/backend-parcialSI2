from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Property
from .serializers import PropertySerializer


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    permission_classes = [IsAuthenticated]

    filterset_fields = ["edificio", "estado"]
    search_fields = ["numero", "propietario", "email", "telefono"]
    ordering_fields = ["numero", "edificio"]
    ordering = ["edificio", "numero"]

    @action(detail=False, methods=["get"])
    def next_number(self, request):
        """
        Sugerir siguiente número libre en un edificio.
        """
        edificio = (request.query_params.get("edificio") or "").upper().strip()
        if not edificio:
            return Response({"error": "Falta parámetro 'edificio'"}, status=400)

        existing = (
            Property.objects.filter(edificio=edificio)
            .values_list("numero", flat=True)
        )
        # Buscar hueco empezando en 101
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






