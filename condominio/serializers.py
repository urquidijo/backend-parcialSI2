import re
from rest_framework import serializers
from .models import Property, PropertyTenant
from users.serializers import UserSerializer  # serializer de tu User


class PropertyTenantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        write_only=True, source="user", queryset=UserSerializer.Meta.model.objects.all()
    )

    class Meta:
        model = PropertyTenant
        fields = ["id", "user", "user_id"]


class PropertySerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    owner_id = serializers.PrimaryKeyRelatedField(
        queryset=UserSerializer.Meta.model.objects.all(),
        source="owner", write_only=True, allow_null=True, required=False
    )
    tenants = PropertyTenantSerializer(many=True, read_only=True)

    # Permite mandar "120 m²"
    area = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Property
        fields = [
            "id", "edificio", "numero",
            "estado", "area_m2", "area",
            "owner", "owner_id", "tenants",
        ]
        extra_kwargs = {"estado": {"required": False}, "area_m2": {"required": False}}

    def _parse_area(self, txt):
        if not txt:
            return None
        m = re.search(r"([\d.,]+)", txt)
        if not m:
            return None
        value = m.group(1).replace(".", "").replace(",", ".")
        try:
            return float(value)
        except ValueError:
            return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["area"] = f"{int(instance.area_m2)} m²" if instance.area_m2 else ""
        return data

    def validate(self, attrs):
        # Área libre-formato -> area_m2
        area_txt = attrs.pop("area", None)
        if area_txt:
            parsed = self._parse_area(area_txt)
            if parsed is not None:
                attrs["area_m2"] = parsed

        # Estado automático: ocupada si hay dueño o inquilinos
        if "estado" not in attrs:
            inst = getattr(self, "instance", None)
            has_owner = bool(attrs.get("owner") or (inst and inst.owner_id))
            has_tenants = bool(inst and inst.tenants.exists())
            attrs["estado"] = "ocupada" if (has_owner or has_tenants) else "disponible"

        return attrs
