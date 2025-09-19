from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import Reporte, Tarea, Material
from .serializers import ReporteSerializer, TareaSerializer, MaterialSerializer


class ReporteViewSet(viewsets.ModelViewSet):
    queryset = Reporte.objects.select_related('responsable','creado_por').order_by('-fecha_inicio')
    serializer_class = ReporteSerializer

    def perform_create(self, serializer):
        user = self.request.user if getattr(self.request.user, 'is_authenticated', False) else None
        serializer.save(creado_por=user)


class TareaViewSet(viewsets.ModelViewSet):
    queryset = Tarea.objects.select_related('asignado_a').order_by('-fecha_programada')
    serializer_class = TareaSerializer

    @action(detail=True, methods=['post'])
    def cambiar_estado(self, request, pk=None):
        tarea = self.get_object()
        estado = request.data.get('estado')
        if estado not in ('pendiente', 'en_progreso', 'completado'):
            return Response({'detail': 'estado inválido'}, status=status.HTTP_400_BAD_REQUEST)

        hoy = timezone.now().date()
        if estado == 'pendiente':
            tarea.estado = 'pendiente'
            tarea.fecha_completada = None
        elif estado == 'en_progreso':
            tarea.estado = 'en_progreso'
            if not tarea.fecha_programada or tarea.fecha_programada > hoy:
                tarea.fecha_programada = hoy
            tarea.fecha_completada = None
        else:
            tarea.estado = 'completado'
            tarea.fecha_completada = request.data.get('fecha_completada') or hoy

        tarea.save()
        return Response(TareaSerializer(tarea).data, status=status.HTTP_200_OK)


class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.select_related('reporte').order_by('-id')
    serializer_class = MaterialSerializer
