# Generated by Django 4.2.2 on 2024-05-03 14:38

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('budo_app', '0031_remove_kinder_kid_alter'),
    ]

    operations = [
        migrations.CreateModel(
            name='Profil',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rufname', models.CharField(blank=True, default='', help_text='Wie willst du genannt werden?', max_length=255)),
                ('allergien', models.CharField(blank=True, default='', max_length=500)),
                ('rolle', models.CharField(blank=True, choices=[('b', 'Betreuer:in'), ('k', 'Küche'), ('o', 'Organisator'), ('f', 'Freiwilliger Helfer')], default='b', help_text='Was ist deine Rolle im Team?', max_length=1)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profil', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Profile',
            },
        ),
    ]
