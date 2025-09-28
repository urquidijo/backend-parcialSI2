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
