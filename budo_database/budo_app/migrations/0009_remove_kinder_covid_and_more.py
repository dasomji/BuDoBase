# Generated by Django 4.2.2 on 2023-07-08 09:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budo_app', '0008_delete_document_alter_kinder_anmerkung_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='kinder',
            name='covid',
        ),
        migrations.AlterField(
            model_name='kinder',
            name='anmelde_organisation',
            field=models.CharField(default='', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='anmelder_email',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='anmerkung_buchung',
            field=models.CharField(max_length=10000, null=True),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='rechnung_plz',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='sex',
            field=models.CharField(max_length=255),
        ),
    ]