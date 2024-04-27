# Generated by Django 4.2.2 on 2024-01-17 13:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budo_app', '0023_alter_kinder_budo_family_notizen'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='notizen',
            options={'verbose_name_plural': 'Notizen'},
        ),
        migrations.AddField(
            model_name='auslagerorte',
            name='koordinaten_parkspot',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='schwerpunkte',
            name='geplante_abreise',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='schwerpunkte',
            name='geplante_ankunft',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]