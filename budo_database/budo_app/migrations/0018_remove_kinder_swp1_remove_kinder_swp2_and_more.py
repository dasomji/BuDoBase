# Generated by Django 4.2.2 on 2024-01-12 11:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('budo_app', '0017_auslagerorte_beschreibung_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='kinder',
            name='swp1',
        ),
        migrations.RemoveField(
            model_name='kinder',
            name='swp2',
        ),
        migrations.AlterField(
            model_name='kinder',
            name='schwerpunkt_woche1',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='kinder_woche1', to='budo_app.schwerpunkte', verbose_name='Schwerpunkt Woche 1'),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='schwerpunkt_woche2',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='kinder_woche2', to='budo_app.schwerpunkte', verbose_name='Schwerpunkt Woche 2'),
        ),
    ]
