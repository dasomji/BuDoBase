# Generated by Django 4.2.2 on 2024-04-25 15:46

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budo_app', '0027_alter_notizen_notiz'),
    ]

    operations = [
        migrations.AddField(
            model_name='turnus',
            name='turnus_beginn',
            field=models.DateField(default=datetime.datetime(2022, 7, 16, 0, 0)),
            preserve_default=False,
        ),
    ]
