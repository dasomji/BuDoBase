# Generated by Django 4.2.2 on 2024-06-08 11:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budo_app', '0049_alter_schwerpunkte_schwerpunktzeit_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='turnus',
            name='uploadedFile',
            field=models.FileField(blank=True, null=True, upload_to='Uploaded Files/'),
        ),
    ]