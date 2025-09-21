from rest_framework import serializers
from .models import Payment, PriceConfig, Charge
from condominio.models import Property


# -------------------------
# PriceConfig
# -------------------------
class PriceConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceConfig
        fields = ["id", "type", "base_price", "active"]

    def validate_base_price(self, v):
        if v is None or v < 0:
            raise serializers.ValidationError("El precio debe ser >= 0.")
        return v


# -------------------------
# Charge
# -------------------------
class ChargeSerializer(serializers.ModelSerializer):
    # lo que mandarás desde Postman
    property_id = serializers.IntegerField(write_only=True)
    price_config_id = serializers.IntegerField(write_only=True)

    # lo que verás en la respuesta
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Charge
        fields = [
            "id",
            "property_id",
            "price_config_id",
            "fecha_pago",
            "status",
            "issued_at",
            "paid_at",
            "amount",
        ]
        read_only_fields = ["status", "issued_at", "paid_at", "amount"]

    def create(self, validated_data):
        # mapear ids a FKs reales
        prop_id = validated_data.pop("property_id")
        price_id = validated_data.pop("price_config_id")

        validated_data["propiedad"] = Property.objects.get(pk=prop_id)
        validated_data["price_config"] = PriceConfig.objects.get(pk=price_id)

        return Charge.objects.create(**validated_data)

    def update(self, instance, validated_data):
        prop_id = validated_data.pop("propiedad_id", None)
        pc_id = validated_data.pop("price_config_id", None)
        if prop_id is not None:
            instance.propiedad_id = prop_id
        if pc_id is not None:
            instance.price_config_id = pc_id
        for f in ("fecha_pago", "status",):
            if f in validated_data:
                setattr(instance, f, validated_data[f])
        instance.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # devuelve también los IDs que la UI necesita
        data["property_id"] = instance.propiedad_id
        data["price_config_id"] = instance.price_config_id
        return data


# -------------------------
# Payment (crear/leer)
# -------------------------
class PaymentSerializer(serializers.ModelSerializer):
    # Conveniencia sólo-lectura
    reservation_id = serializers.IntegerField(source="reservation.id", read_only=True)
    charge_id = serializers.IntegerField(source="charge.id", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "reservation",      # enviar id si es reserva
            "charge",           # o enviar id si es cargo
            "reservation_id",
            "charge_id",
            "amount",
            "status",
            "stripe_session_id",
            "stripe_payment_intent_id",
            "receipt_url",
        ]
        read_only_fields = [
            "status",
            "stripe_session_id",
            "stripe_payment_intent_id",
            "receipt_url",
        ]


# -------------------------
# Payment list para reservas (historial mío)
# -------------------------
class PaymentListSerializer(serializers.ModelSerializer):
    reservation_id = serializers.IntegerField(source="reservation.id", read_only=True)
    area_id = serializers.IntegerField(source="reservation.area.id", read_only=True)
    area_nombre = serializers.CharField(source="reservation.area.nombre", read_only=True)
    fecha_reserva = serializers.DateField(source="reservation.fecha_reserva", read_only=True)
    hora_inicio = serializers.TimeField(source="reservation.hora_inicio", read_only=True)
    hora_fin = serializers.TimeField(source="reservation.hora_fin", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "reservation_id",
            "area_id",
            "area_nombre",
            "fecha_reserva",
            "hora_inicio",
            "hora_fin",
            "amount",
            "status",
            "receipt_url",
        ]
