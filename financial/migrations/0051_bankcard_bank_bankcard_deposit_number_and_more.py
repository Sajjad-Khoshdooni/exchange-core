# Generated by Django 4.0 on 2022-08-14 13:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0050_bankcard_kyc_historicalbankcard_kyc_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='bankcard',
            name='bank',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='bankcard',
            name='deposit_number',
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='bankcard',
            name='owner_name',
            field=models.CharField(blank=True, max_length=256),
        ),
        migrations.AddField(
            model_name='bankcard',
            name='reject_reason',
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='bankcard',
            name='type',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='historicalbankcard',
            name='bank',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='historicalbankcard',
            name='deposit_number',
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='historicalbankcard',
            name='owner_name',
            field=models.CharField(blank=True, max_length=256),
        ),
        migrations.AddField(
            model_name='historicalbankcard',
            name='reject_reason',
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name='historicalbankcard',
            name='type',
            field=models.CharField(blank=True, max_length=64),
        ),
    ]
