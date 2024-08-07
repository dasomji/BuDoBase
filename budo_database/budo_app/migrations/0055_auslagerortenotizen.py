# Generated by Django 5.0.6 on 2024-07-03 12:54

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budo_app', '0054_auslagerorteimage'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuslagerorteNotizen',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notiz', models.TextField(blank=True, null=True)),
                ('date_added', models.DateTimeField(auto_now_add=True)),
                ('added_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('auslagerort', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='auslagernotizen', to='budo_app.auslagerorte')),
            ],
            options={
                'verbose_name_plural': 'Auslagerorte Notizen',
            },
        ),
    ]
