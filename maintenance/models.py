from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum

User = settings.AUTH_USER_MODEL

TIPOS_MTTO = [('preventivo', 'Preventivo'), ('correctivo', 'Correctivo')]
PRIORIDADES = [('baja', 'Baja'), ('media', 'Media'), ('alta', 'Alta')]
DESTINATARIOS = [('interno', 'Personal Interno'), ('externo', 'Personal Externo')]
ESTADOS = [('pendiente', 'Pendiente'), ('en_progreso', 'En Progreso'), ('completado', 'Completado')]


class Reporte(models.Model):
    tipo = models.CharField(max_length=20, choices=TIPOS_MTTO)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    ubicacion = models.CharField(max_length=200)
    prioridad = models.CharField(max_length=20, choices=PRIORIDADES)
    asignar_a = models.CharField(max_length=10, choices=DESTINATARIOS, default='interno')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reportes_asignados')
    costo_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reportes_creados')

    @property
    def estado(self):
        if self.fecha_fin and self.fecha_fin < timezone.now().date():
            return "completado"
        return "pendiente"

    def __str__(self):
        return f"{self.titulo} ({self.tipo})"


class Tarea(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPOS_MTTO)
    prioridad = models.CharField(max_length=20, choices=PRIORIDADES)

    # Estado persistente (antes era @property)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')

    asignar_a = models.CharField(max_length=10, choices=DESTINATARIOS, default='interno')
    fecha_programada = models.DateField()
    fecha_completada = models.DateField(null=True, blank=True)
    costo_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    ubicacion = models.CharField(max_length=200)
    asignado_a = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='tareas_asignadas')

    def save(self, *args, **kwargs):
        hoy = timezone.now().date()
        if self.estado == 'completado' and not self.fecha_completada:
            self.fecha_completada = hoy
        if self.estado == 'en_progreso' and self.fecha_programada and self.fecha_programada > hoy:
            self.fecha_programada = hoy
        if self.estado == 'pendiente':
            self.fecha_completada = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titulo


class Material(models.Model):
    reporte = models.ForeignKey(Reporte, on_delete=models.CASCADE, related_name='materiales')
    nombre = models.CharField(max_length=200)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    unidad = models.CharField(max_length=100)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    costo_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    def save(self, *args, **kwargs):
        self.costo_total = (self.cantidad or 0) * (self.costo_unitario or 0)
        super().save(*args, **kwargs)
        self._recalc_reporte()

    def delete(self, *args, **kwargs):
        rep = self.reporte
        super().delete(*args, **kwargs)
        if rep_id := getattr(rep, "id", None):
            self._recalc_reporte(rep)

    def _recalc_reporte(self, rep=None):
        rep = rep or self.reporte
        total = rep.materiales.aggregate(s=Sum('costo_total'))['s'] or Decimal('0.00')
        rep.costo_total = total
        rep.save(update_fields=['costo_total'])

    def __str__(self):
        return f"{self.nombre} ({self.cantidad} {self.unidad})"
