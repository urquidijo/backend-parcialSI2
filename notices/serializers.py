from rest_framework import serializers
from .models import Notice

class NoticeSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Notice
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at"]
