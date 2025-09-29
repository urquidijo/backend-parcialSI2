# bitacora/serializers.py
from rest_framework import serializers
from .models import Bitacora

class BitacoraSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Bitacora
        fields = ["id", "usuario", "usuario_nombre", "ip", "fecha_entrada", "hora_entrada", "acciones", "estado"]
        extra_kwargs = {
            "usuario": {"write_only": True},
            "ip": {"read_only": True},
            "fecha_entrada": {"read_only": True},  # ✅ evita el 400
            "hora_entrada": {"read_only": True},   # ✅ evita el 400       # Se llena automáticamente
        }

    def get_usuario_nombre(self, obj):
        return f"{obj.usuario.first_name} {obj.usuario.last_name}".strip()

    def create(self, validated_data):
        # Agregar IP desde request
        request = self.context.get("request")
        if request:
            validated_data["ip"] = self.get_client_ip(request)
        return super().create(validated_data)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
