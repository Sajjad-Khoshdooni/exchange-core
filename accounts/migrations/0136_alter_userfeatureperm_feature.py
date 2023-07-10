# Generated by Django 4.1.3 on 2023-07-10 10:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0135_delete_externalnotification'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userfeatureperm',
            name='feature',
            field=models.CharField(choices=[('pay_id', 'pay_id'), ('fiat_deposit_daily_limit', 'fiat_deposit_daily_limit'), ('bank_payment', 'bank_payment')], max_length=32, verbose_name='ویژگی'),
        ),
    ]
