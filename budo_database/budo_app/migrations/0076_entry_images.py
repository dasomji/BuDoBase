import budo_app.private_storage
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


IMAGE_FIELDS = [
    (
        "datei",
        models.FileField(
            storage=budo_app.private_storage.attachment_storage,
            upload_to="",
            validators=[
                django.core.validators.RegexValidator(
                    "\\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\\.webp\\Z",
                    "Bilder benötigen einen opaken WebP-Speicherschlüssel.",
                )
            ],
        ),
    ),
    ("position", models.PositiveIntegerField()),
    ("width", models.PositiveIntegerField()),
    ("height", models.PositiveIntegerField()),
    (
        "checksum",
        models.CharField(
            max_length=64,
            validators=[
                django.core.validators.RegexValidator(
                    "\\A[0-9a-f]{64}\\Z",
                    "Die Prüfsumme muss ein kleingeschriebener SHA-256-Wert sein.",
                )
            ],
        ),
    ),
]


class Migration(migrations.Migration):
    dependencies = [("budo_app", "0075_erstehilfeeintrag")]

    operations = [
        migrations.CreateModel(
            name="NotizFoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                *IMAGE_FIELDS,
                ("eintrag", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fotos", to="budo_app.notizen")),
            ],
            options={"verbose_name": "Notizfoto", "verbose_name_plural": "Notizfotos", "ordering": ("position", "id")},
        ),
        migrations.CreateModel(
            name="ErsteHilfeFoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                *IMAGE_FIELDS,
                ("eintrag", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fotos", to="budo_app.erstehilfeeintrag")),
            ],
            options={"verbose_name": "EH-Foto", "verbose_name_plural": "EH-Fotos", "ordering": ("position", "id")},
        ),
        migrations.AddConstraint(
            model_name="notizfoto",
            constraint=models.UniqueConstraint(fields=("eintrag", "position"), name="notiz_foto_eintrag_position_uniq"),
        ),
        migrations.AddConstraint(
            model_name="erstehilfefoto",
            constraint=models.UniqueConstraint(fields=("eintrag", "position"), name="eh_foto_eintrag_position_uniq"),
        ),
    ]
