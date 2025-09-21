# condominio/models.py
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from users.models import User


class Property(models.Model):
    ESTADO_CHOICES = (
        ("ocupada", "Ocupada"),
        ("disponible", "Disponible"),
    )

    edificio = models.CharField(max_length=1)                 # Ej: A, B
    numero   = models.CharField(max_length=20, unique=True)   # Ej: A-101

    # DUEÑO (1)
    owner = models.ForeignKey(
        User, null=True, blank=True,
        related_name="properties_owned",
        on_delete=models.SET_NULL,
    )

    estado  = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="disponible")
    area_m2 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "property"
        ordering = ["edificio", "numero"]

    def __str__(self):
        return self.numero

    def refresh_estado(self, save=True):
        """
        Si hay al menos un inquilino, 'ocupada', si no 'disponible'.
        """
        nueva = "ocupada" if self.tenants.exists() else "disponible"
        if nueva != self.estado:
            self.estado = nueva
            if save:
                self.save(update_fields=["estado"])


class PropertyTenant(models.Model):
    """
    Inquilinos simultáneos por propiedad (sin historial ni relación).
    Cada fila = un usuario viviendo en una propiedad.
    """
    property = models.ForeignKey(Property, related_name="tenants", on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name="properties_as_tenant", on_delete=models.CASCADE)

    class Meta:
        db_table = "property_tenant"
        unique_together = (("property", "user"),)  # Evita duplicados del mismo inquilino
        indexes = [
            models.Index(fields=["property", "user"]),
        ]

    def __str__(self):
        return f"{self.user.email} ↔ {self.property.numero}"


# ---- Señales: mantener 'estado' actualizado cuando cambian inquilinos ----
@receiver(post_save, sender=PropertyTenant)
def _on_tenant_added(sender, instance, created, **kwargs):
    instance.property.refresh_estado()

@receiver(post_delete, sender=PropertyTenant)
def _on_tenant_removed(sender, instance, **kwargs):
    instance.property.refresh_estado()
