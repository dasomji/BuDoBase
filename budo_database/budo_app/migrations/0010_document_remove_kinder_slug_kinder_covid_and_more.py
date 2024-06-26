# Generated by Django 4.2.2 on 2023-07-10 16:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budo_app', '0009_remove_kinder_covid_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('uploadedFile', models.FileField(upload_to='Uploaded Files/')),
                ('dateTimeOfUpload', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.RemoveField(
            model_name='kinder',
            name='slug',
        ),
        migrations.AddField(
            model_name='kinder',
            name='covid',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='anmelde_organisation',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='anmelder_email',
            field=models.CharField(default=None, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='anmerkung',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='anmerkung_buchung',
            field=models.CharField(default=None, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='anmerkung_team',
            field=models.CharField(default='', max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='early_abreise_abholer',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='early_abreise_reason',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='hauptversichert_bei',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='notfall_kontakte',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='rechnung_plz',
            field=models.IntegerField(default=None, null=True),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='sex',
            field=models.CharField(default=None, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='kinder',
            name='zeltwunsch',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
