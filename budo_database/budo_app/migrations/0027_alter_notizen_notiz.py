# Generated by Django 4.2.2 on 2024-04-17 13:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budo_app', '0026_kinder_wo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notizen',
            name='notiz',
            field=models.TextField(blank=True, null=True),
        ),
    ]
