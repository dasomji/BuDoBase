# Generated by Django 4.2.2 on 2024-05-05 16:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budo_app', '0041_alter_meal_meal_choice'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schwerpunktzeit',
            name='woche',
            field=models.CharField(choices=[('w1', 'Woche 1'), ('w2', 'Woche 2'), ('u', 'unklar')], default='u', max_length=2, unique=True),
        ),
    ]
