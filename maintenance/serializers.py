from rest_framework import serializers
from .models import Reporte, Tarea, Material


class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = ['id', 'reporte', 'nombre', 'cantidad', 'unidad', 'costo_unitario', 'costo_total']
        read_only_fields = ['id', 'costo_total']


class MaterialNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = ['id', 'nombre', 'cantidad', 'unidad', 'costo_unitario', 'costo_total']
        read_only_fields = ['id', 'costo_total']


class TareaSerializer(serializers.ModelSerializer):
    # estado ahora es editable (no ReadOnlyField)
    class Meta:
        model = Tarea
        fields = [
            'id','titulo','descripcion','tipo','prioridad','estado','asignar_a',
            'fecha_programada','fecha_completada','costo_estimado','ubicacion','asignado_a'
        ]


class ReporteSerializer(serializers.ModelSerializer):
    materiales = MaterialNestedSerializer(many=True, required=False)
    creado_por = serializers.HiddenField(default=serializers.CurrentUserDefault())
    estado = serializers.ReadOnlyField()

    class Meta:
        model = Reporte
        fields = [
            'id','tipo','titulo','descripcion','ubicacion','prioridad','estado','asignar_a',
            'fecha_inicio','fecha_fin','responsable','materiales','costo_total','creado_por'
        ]
        read_only_fields = ['costo_total','estado']

    def create(self, validated_data):
        materiales_data = validated_data.pop('materiales', [])
        reporte = Reporte.objects.create(**validated_data)
        for m in materiales_data:
            Material.objects.create(reporte=reporte, **m)
        return reporte

    def update(self, instance, validated_data):
        materiales_data = validated_data.pop('materiales', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if materiales_data is not None:
            instance.materiales.all().delete()
            for m in materiales_data:
                Material.objects.create(reporte=instance, **m)
        return instance
