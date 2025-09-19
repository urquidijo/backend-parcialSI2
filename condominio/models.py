from django.db import models

class Property(models.Model):
    ESTADO_CHOICES = (
        ("ocupada", "Ocupada"),
        ("disponible", "Disponible"),
    )

    edificio = models.CharField(max_length=1)   # Ej: A, B
    numero = models.CharField(max_length=20, unique=True)  # Ej: A-101

    propietario = models.CharField(max_length=150, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="disponible")
    area_m2 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "property"
        ordering = ["edificio", "numero"]

    def __str__(self):
        return self.numero
