# bitacora/views.py
from rest_framework import generics
from .models import Bitacora
from .serializers import BitacoraSerializer

class BitacoraListCreateView(generics.ListCreateAPIView):
    queryset = Bitacora.objects.all()
    serializer_class = BitacoraSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
    
    def get_queryset(self):
        # ya está ordenado por -fecha_entrada y -hora_entrada en el modelo
        return Bitacora.objects.all()[:30]  # 👈 trae solo las últimas 20
