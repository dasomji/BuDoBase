# Generated by Django 4.2.2 on 2024-04-25 15:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('budo_app', '0028_turnus_turnus_beginn'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='turnus',
            name='turnus_year',
        ),
    ]