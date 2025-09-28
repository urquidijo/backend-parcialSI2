from rest_framework import serializers
from ai.models import UserFace
from users.models import User

class FaceEnrollSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    file = serializers.ImageField()

    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Usuario no existe")
        return value

class FaceStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFace
        fields = ["user", "external_image_id", "face_id", "collection_id", "status", "s3_key", "created_at", "updated_at"]



from rest_framework import serializers
from ai.models.plate import Plate

class PlateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plate
        fields = ["id", "number", "user"]



import os, boto3
from rest_framework import serializers
from ai.models.alert import Alert

REGION        = os.getenv("AWS_REGION", "us-east-1")
INPUT_BUCKET  = os.getenv("AWS_STORAGE_BUCKET_NAME", "").strip()
OUTPUT_BUCKET = (os.getenv("ALERTS_BUCKET", "").strip() or INPUT_BUCKET)
_s3 = boto3.client("s3", region_name=REGION)

class AlertSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    type_label = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = [
            "id","type","type_label","camera_id",
            "s3_video_key","s3_image_key","image_url",
            "timestamp_ms","confidence","extra","created_at"
        ]

    def get_type_label(self, obj: Alert) -> str:
        return {
            "dog_loose": "Perro suelto",
            "dog_waste": "Perro haciendo necesidades",
            "bad_parking": "Mal estacionado",
        }.get(obj.type, obj.type)

    def _presign(self, bucket: str, key: str) -> str:
        return _s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=3600,
        )

    def get_image_url(self, obj: Alert) -> str | None:
        key = obj.s3_image_key
        if not key:
            return None
        try:
            return self._presign(OUTPUT_BUCKET, key)
        except Exception:
            pass
        try:
            return self._presign(INPUT_BUCKET, key)
        except Exception:
            return None
