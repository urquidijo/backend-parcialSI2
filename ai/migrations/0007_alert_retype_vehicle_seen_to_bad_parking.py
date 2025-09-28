from django.db import migrations

def forward(apps, schema_editor):
    Alert = apps.get_model("ai", "Alert")
    # Convierte TODO lo viejo 'vehicle_seen' a 'bad_parking'
    Alert.objects.filter(type="vehicle_seen").update(type="bad_parking")

def backward(apps, schema_editor):
    # No hay vuelta necesaria; si quisieras revertir:
    pass

class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0006_alert"),  # ajusta si tu numeración es distinta
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
