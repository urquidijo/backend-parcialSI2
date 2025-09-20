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
