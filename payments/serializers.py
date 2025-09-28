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

def _prop_label(prop) -> str:
    """
    Intenta construir un label legible de la propiedad.
    Ajusta los nombres de campos según tu modelo Property.
    """
    if not prop:
        return ""
    # ejemplos típicos de campo
    edificio = getattr(prop, "edificio", None) or getattr(prop, "tower", None)
    numero = getattr(prop, "numero", None) or getattr(prop, "unit", None)
    name = getattr(prop, "name", None)

    if edificio and numero:
        return f"{edificio} - {numero}"
    if name:
        return str(name)
    # fallback a __str__
    return str(prop)


# ======================================================
# 1) Serializer "bonito" para listar cargos (solo lectura)
#    Usado por ChargeViewSet(list/retrieve/summary) y MyChargesViewSet
#    Devuelve EXACTAMENTE los campos que tu app espera.
# ======================================================
class ChargeListSerializer(serializers.ModelSerializer):
    property_id = serializers.IntegerField(source="propiedad_id", read_only=True)
    property_label = serializers.SerializerMethodField()
    price_type = serializers.CharField(source="price_config.type", read_only=True)
    # amount: puedes tomarlo de la relación o de la @property amount del modelo
    amount = serializers.DecimalField(source="price_config.base_price", max_digits=10, decimal_places=2, read_only=True)
    # Si prefieres usar la @property amount del modelo:
    # amount = serializers.SerializerMethodField()

    class Meta:
        model = Charge
        fields = [
            "id",
            "property_id",
            "property_label",
            "price_type",
            "amount",
            "status",
            "issued_at",
            "fecha_pago",
            "paid_at",
        ]
        read_only_fields = fields

    def get_property_label(self, obj):
        return _prop_label(getattr(obj, "propiedad", None))

    # Si usas la @property amount del modelo:
    # def get_amount(self, obj):
    #     return f"{obj.amount:.2f}"


# ======================================================
# 2) Serializer de lectura para historial de pagos
#    (cubre pagos por cargo y por reserva)
# ======================================================
class PaymentReadSerializer(serializers.ModelSerializer):
    # IDs convenientes
    charge_id = serializers.IntegerField(source="charge.id", read_only=True)
    reservation_id = serializers.IntegerField(source="reservation.id", read_only=True)

    # Campos "bonitos" según exista charge o reserva
    price_type = serializers.SerializerMethodField()       # p.ej. tipo de cargo
    property_id = serializers.SerializerMethodField()
    property_label = serializers.SerializerMethodField()

    # Para reservas (si las usas en el app)
    area_id = serializers.SerializerMethodField()
    area_nombre = serializers.SerializerMethodField()
    fecha_reserva = serializers.SerializerMethodField()
    hora_inicio = serializers.SerializerMethodField()
    hora_fin = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "charge_id",
            "reservation_id",
            "amount",
            "status",
            "receipt_url",

            # info de cargo (si aplica)
            "price_type",
            "property_id",
            "property_label",

            # info de reserva (si aplica)
            "area_id",
            "area_nombre",
            "fecha_reserva",
            "hora_inicio",
            "hora_fin",
        ]
        read_only_fields = fields

    # ---------- charge helpers ----------
    def get_price_type(self, obj):
        ch = getattr(obj, "charge", None)
        if ch and ch.price_config:
            return ch.price_config.type
        # para reservas podrías retornar nombre del área, si quieres
        res = getattr(obj, "reservation", None)
        if res and getattr(res, "area", None):
            return f"Reserva - {res.area.nombre}"
        return None

    def get_property_id(self, obj):
        ch = getattr(obj, "charge", None)
        return getattr(ch, "propiedad_id", None) if ch else None

    def get_property_label(self, obj):
        ch = getattr(obj, "charge", None)
        return _prop_label(getattr(ch, "propiedad", None)) if ch else None

    # ---------- reserva helpers ----------
    def get_area_id(self, obj):
        res = getattr(obj, "reservation", None)
        return getattr(getattr(res, "area", None), "id", None) if res else None

    def get_area_nombre(self, obj):
        res = getattr(obj, "reservation", None)
        return getattr(getattr(res, "area", None), "nombre", None) if res else None

    def get_fecha_reserva(self, obj):
        res = getattr(obj, "reservation", None)
        return getattr(res, "fecha_reserva", None) if res else None

    def get_hora_inicio(self, obj):
        res = getattr(obj, "reservation", None)
        return getattr(res, "hora_inicio", None) if res else None

    def get_hora_fin(self, obj):
        res = getattr(obj, "reservation", None)
        return getattr(res, "hora_fin", None) if res else None

