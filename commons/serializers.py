# commons/serializers.py
from rest_framework import serializers
from .models import AreaComun, ReservaAreaComun

# ---------- ÁREAS ----------
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
            "precio",
        ]


# ---------- RESERVAS ----------
class ReservaAreaComunSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source="usuario.username", read_only=True)
    area_nombre = serializers.CharField(source="area.nombre", read_only=True)
    # precio solo-lectura (viene del área)
    precio = serializers.DecimalField(max_digits=10, decimal_places=2, source="area.precio", read_only=True)

    # nueva: fecha en que la reserva quedó APROBADA (solo fecha)
    approved_at = serializers.DateField(read_only=True)

    # (opcionales de pagos si usas payments)
    paid = serializers.SerializerMethodField(read_only=True)
    payment_status = serializers.SerializerMethodField(read_only=True)
    receipt_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ReservaAreaComun
        fields = [
            "id",
            "usuario", "usuario_username",
            "area", "area_nombre",
            "fecha_reserva", "hora_inicio", "hora_fin",
            "estado",
            "precio",
            "approved_at",              # <- aquí exponemos la fecha de aprobación
            "paid", "payment_status", "receipt_url",
        ]
        read_only_fields = ["usuario", "precio", "approved_at", "paid", "payment_status", "receipt_url"]

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        ini = attrs.get("hora_inicio") or (instance.hora_inicio if instance else None)
        fin = attrs.get("hora_fin") or (instance.hora_fin if instance else None)
        if ini and fin and ini >= fin:
            raise serializers.ValidationError("hora_fin debe ser mayor que hora_inicio.")
        return attrs

    def create(self, validated_data):
        validated_data["usuario"] = self.context["request"].user
        return super().create(validated_data)

    def get_paid(self, obj):
        pay = getattr(obj, "payment", None)
        return bool(pay and getattr(pay, "status", "") == "SUCCEEDED")

    def get_payment_status(self, obj):
        pay = getattr(obj, "payment", None)
        return getattr(pay, "status", None) if pay else None

    def get_receipt_url(self, obj):
        pay = getattr(obj, "payment", None)
        return getattr(pay, "receipt_url", None) if pay else None


# ---------- REPORTES ----------
class UsageReportRowSerializer(serializers.Serializer):
    """
    'fecha_aprobada' = día en que la reserva fue APROBADA (approved_at), sin hora.
    """
    id = serializers.IntegerField()
    area_nombre = serializers.CharField()
    residente = serializers.CharField()
    departamento = serializers.CharField(allow_null=True)
    fecha_aprobada = serializers.DateField(allow_null=True)
    hora_inicio = serializers.TimeField()
    hora_fin = serializers.TimeField()
    precio = serializers.DecimalField(max_digits=10, decimal_places=2)
    pago_monto = serializers.DecimalField(max_digits=10, decimal_places=2)
    pago_estado = serializers.CharField()
    pago_recibo = serializers.CharField(allow_blank=True)
