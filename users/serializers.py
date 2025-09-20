from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Role, Permission

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "name", "code", "description"]

class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, queryset=Permission.objects.all(),
        source="permissions", required=False
    )
    class Meta:
        model = Role
        fields = ["id", "name", "description", "permissions", "permission_ids"]

class UserSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source="role", write_only=True, allow_null=True
    )
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "password", "role", "role_id"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
    

from .models import Permission  # si no lo tenías importado

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        # 🔹 Incluimos ID del usuario
        data["id"] = self.user.id  

        # 🔹 Info de rol
        data["role"] = self.user.role.name if self.user.role else None

        # 🔹 Permisos asociados al rol
        role_perms = self.user.role.permissions.all() if self.user.role else Permission.objects.none()
        data["permissions"] = [p.code for p in role_perms]

        # 🔹 Datos básicos del usuario
        data["email"] = self.user.email
        data["first_name"] = self.user.first_name
        data["last_name"] = self.user.last_name

        return data