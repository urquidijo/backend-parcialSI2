from rest_framework import serializers

class IndicadorSerializer(serializers.Serializer):
    name = serializers.CharField()
    value = serializers.FloatField()
