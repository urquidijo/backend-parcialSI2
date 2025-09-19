import re
from rest_framework import serializers
from .models import Property


class PropertySerializer(serializers.ModelSerializer):
    # Permite mandar "120 m²" y guardarlo como número
    area = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Property
        fields = [
            "id",
            "edificio",
            "numero",
            "propietario",
            "telefono",
            "email",
            "estado",
            "area_m2",
            "area",
        ]
        extra_kwargs = {
            "estado": {"required": False},
            "area_m2": {"required": False},
        }

    def _parse_area(self, txt):
        if not txt:
            return None
        match = re.search(r"([\d.,]+)", txt)
        if not match:
            return None
        value = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(value)
        except ValueError:
            return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Formato para mostrar "120 m²"
        data["area"] = f"{int(instance.area_m2)} m²" if instance.area_m2 else ""
        return data

    def validate(self, attrs):
        # Área
        area_txt = attrs.pop("area", None)
        if area_txt:
            parsed = self._parse_area(area_txt)
            if parsed is not None:
                attrs["area_m2"] = parsed

        # Estado automático según propietario
        if "estado" not in attrs:
            propietario = attrs.get("propietario", getattr(self.instance, "propietario", ""))
            attrs["estado"] = "ocupada" if propietario else "disponible"

        return attrs
