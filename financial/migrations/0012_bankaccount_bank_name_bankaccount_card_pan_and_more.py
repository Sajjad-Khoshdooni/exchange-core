# Generated by Django 4.0 on 2022-02-23 09:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0011_alter_fiatwithdrawrequest_lock'),
    ]

    operations = [
        migrations.AddField(
            model_name='bankaccount',
            name='bank_name',
            field=models.CharField(blank=True, max_length=256),
        ),
        migrations.AddField(
            model_name='bankaccount',
            name='card_pan',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='bankaccount',
            name='deposit_address',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='bankaccount',
            name='deposit_status',
            field=models.CharField(blank=True, choices=[('active', 'active'), ('suspend', 'suspend'), ('nsuspend', 'nodep suspend'), ('stagnant', 'stagnant')], max_length=8),
        ),
        migrations.AddField(
            model_name='bankaccount',
            name='owners',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='bankaccount',
            name='verified',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='bankcard',
            name='verified',
            field=models.BooleanField(blank=True, null=True),
        ),
    ]