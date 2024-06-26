# Generated by Django 4.2.2 on 2024-06-08 11:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('budo_app', '0050_alter_turnus_uploadedfile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schwerpunktzeit',
            name='turnus',
            field=models.ForeignKey(help_text='In welchem Turnus findet dieser Schwerpunkt statt?', null=True, on_delete=django.db.models.deletion.CASCADE, to='budo_app.turnus'),
        ),
        migrations.AlterField(
            model_name='schwerpunktzeit',
            name='woche',
            field=models.CharField(choices=[('w1', 'Woche 1'), ('w2', 'Woche 2'), ('u', 'unklar')], default='u', max_length=2),
        ),
        migrations.AlterUniqueTogether(
            name='schwerpunktzeit',
            unique_together={('turnus', 'woche')},
        ),
    ]
