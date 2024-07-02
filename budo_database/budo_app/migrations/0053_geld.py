# Generated by Django 4.2.2 on 2024-07-02 12:54

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('budo_app', '0052_auslagerorte_kontakt'),
    ]

    operations = [
        migrations.CreateModel(
            name='Geld',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.FloatField(blank=True, null=True)),
                ('date_added', models.DateTimeField(auto_now_add=True)),
                ('added_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('kinder', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='geld', to='budo_app.kinder')),
            ],
            options={
                'verbose_name_plural': 'Taschengeld',
            },
        ),
    ]