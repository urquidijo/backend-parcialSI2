from rest_framework import serializers
from .models import AreaComun, ReservaAreaComun

class AreaComunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AreaComun
        fields = [
            "id",
            "nombre",
            "descripcion",
            "capacidad",
            "ubicacion",
            "estado",
            "horario_apertura",
            "horario_cierre",
        ]


class ReservaAreaComunSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source="usuario.username", read_only=True)
    area_nombre = serializers.CharField(source="area.nombre", read_only=True)

    class Meta:
        model = ReservaAreaComun
        fields = [
            "id",
            "usuario", "usuario_username",
            "area", "area_nombre",
            "fecha_reserva", "hora_inicio", "hora_fin",
            "estado",
        ]
        read_only_fields = ["usuario", "estado"]

    def validate(self, attrs):
        # instancia para update
        instance = getattr(self, "instance", None)

        area = attrs.get("area") or (instance.area if instance else None)
        fecha = attrs.get("fecha_reserva") or (instance.fecha_reserva if instance else None)
        ini = attrs.get("hora_inicio") or (instance.hora_inicio if instance else None)
        fin = attrs.get("hora_fin") or (instance.hora_fin if instance else None)

        if not (area and fecha and ini and fin):
            return attrs

        if ini >= fin:
            raise serializers.ValidationError("hora_fin debe ser mayor que hora_inicio.")

        # El solapamiento real igual lo valida models.clean(), pero dejamos este guardado simple:
        from django.db.models import Q
        qs = (ReservaAreaComun.objects
              .filter(area=area, fecha_reserva=fecha, estado__in=["PENDIENTE", "APROBADA"])
              .filter(hora_inicio__lt=fin, hora_fin__gt=ini))
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe una reserva que se superpone.")

        return attrs

    def create(self, validated_data):
        validated_data["usuario"] = self.context["request"].user
        return super().create(validated_data)
