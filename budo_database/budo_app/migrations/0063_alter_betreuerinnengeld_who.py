# Generated by Django 5.0.6 on 2024-07-16 23:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budo_app', '0062_betreuerinnengeld'),
    ]

    operations = [
        migrations.AlterField(
            model_name='betreuerinnengeld',
            name='who',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='betreuerinnen_geld', to='budo_app.profil'),
        ),
    ]
