from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models

class Permission(models.Model):
    # Ej: "view_users", "view_notices", "view:file:/reportes/*"
    name = models.CharField(max_length=80)
    code = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "permission"

    def __str__(self):
        return self.code


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)

    class Meta:
        db_table = "role"

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El usuario debe tener un correo electrónico")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    # No hay is_superuser/is_staff/is_active
    def create_superuser(self, email, password=None, **extra_fields):
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser):
    first_name = models.CharField(max_length=150, blank=True)
    last_name  = models.CharField(max_length=150, blank=True)
    email      = models.EmailField(unique=True)

    role = models.ForeignKey(
        Role, related_name="users", on_delete=models.SET_NULL, null=True, blank=True
    )

    # quitar last_login
    last_login = None

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "user"

    def __str__(self):
        return self.email

    def get_all_permissions(self):
        if not self.role:
            return Permission.objects.none()
        return self.role.permissions.all()
