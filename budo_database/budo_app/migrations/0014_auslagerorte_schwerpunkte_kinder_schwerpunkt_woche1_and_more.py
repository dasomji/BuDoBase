# Generated by Django 4.2.2 on 2024-01-11 13:38

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('budo_app', '0013_alter_kinder_budo_family'),
    ]

    operations = [
        migrations.CreateModel(
            name='Auslagerorte',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('strasse', models.CharField(max_length=255, verbose_name='Straße')),
                ('ort', models.CharField(max_length=100, verbose_name='Stadt')),
                ('bundesland', models.CharField(max_length=100, verbose_name='Bundesland')),
                ('postleitzahl', models.CharField(max_length=20, verbose_name='Postleitzahl')),
                ('land', models.CharField(default='Österreich', max_length=100, verbose_name='Land')),
                ('koordinaten', models.CharField(blank=True, max_length=255, null=True)),
                ('maps_link', models.URLField(blank=True, verbose_name='Google Maps Link')),
            ],
        ),
        migrations.CreateModel(
            name='Schwerpunkte',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('swp_name', models.CharField(max_length=255)),
                ('beschreibung', models.TextField()),
                ('welche_woche', models.CharField(choices=[(0, 'Unbekannt'), (1, 'Woche 1'), (2, 'Woche 2')], default=0, max_length=10)),
                ('betreuende', models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL)),
                ('ort', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='budo_app.auslagerorte')),
            ],
        ),
        migrations.AddField(
            model_name='kinder',
            name='schwerpunkt_woche1',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='kinder_woche1', to='budo_app.schwerpunkte'),
        ),
        migrations.AddField(
            model_name='kinder',
            name='schwerpunkt_woche2',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='kinder_woche2', to='budo_app.schwerpunkte'),
        ),
    ]
