from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models


# -------------------------------
#  PERMISSION
# -------------------------------
class Permission(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "permission"

    def __str__(self):
        return self.code


# -------------------------------
#  ROLE
# -------------------------------
class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)

    class Meta:
        db_table = "role"

    def __str__(self):
        return self.name


# -------------------------------
#  CUSTOM USER MANAGER
# -------------------------------
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El usuario debe tener un correo electrónico")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)



# -------------------------------
#  USER (LOGIN POR EMAIL)
# -------------------------------
class User(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(unique=True)

    role = models.ForeignKey(Role, related_name="users", on_delete=models.SET_NULL, null=True, blank=True)
    extra_permissions = models.ManyToManyField(Permission, related_name="users", blank=True)  # 👈 lo devuelvo

    USERNAME_FIELD = "email"   # login con email
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "user"

    def __str__(self):
        return self.email

    def get_all_permissions(self):
        role_perms = self.role.permissions.all() if self.role else Permission.objects.none()
        direct_perms = self.extra_permissions.all()
        return (role_perms | direct_perms).distinct()

