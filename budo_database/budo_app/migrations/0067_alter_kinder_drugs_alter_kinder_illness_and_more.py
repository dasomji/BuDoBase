# Generated by Django 5.1.3 on 2025-07-12 16:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budo_app', '0066_alter_kinder_anmerkung_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='kinder',
            name='drugs',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='illness',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='rezeptfreie_medikamente',
            field=models.TextField(blank=True, null=True),
        ),
    ]
