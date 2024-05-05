# Generated by Django 4.2.2 on 2024-05-05 22:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budo_app', '0042_alter_schwerpunktzeit_woche'),
    ]

    operations = [
        migrations.AlterField(
            model_name='meal',
            name='meal_type',
            field=models.CharField(choices=[('breakfast', 'Frühstück'), ('lunch', 'Mittagessen'), ('dinner', 'Abendessen')], max_length=10),
        ),
    ]
