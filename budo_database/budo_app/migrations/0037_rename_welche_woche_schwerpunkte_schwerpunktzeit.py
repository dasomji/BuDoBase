# Generated by Django 4.2.2 on 2024-05-05 15:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('budo_app', '0036_alter_schwerpunkte_beschreibung_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='schwerpunkte',
            old_name='welche_woche',
            new_name='Schwerpunktzeit',
        ),
    ]