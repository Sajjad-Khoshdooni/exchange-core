# Generated by Django 4.1.3 on 2023-10-31 14:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0161_remove_company_verified_company_status'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='userfeatureperm',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='userfeatureperm',
            name='custom',
            field=models.CharField(blank=True, max_length=64, verbose_name='پارامتر اختصاصی'),
        ),
        migrations.AlterField(
            model_name='userfeatureperm',
            name='feature',
            field=models.CharField(choices=[('pay_id', 'pay_id'), ('fiat_deposit_daily_limit', 'fiat_deposit_daily_limit'), ('bank_payment', 'bank_payment'), ('ui', 'ui')], max_length=32, verbose_name='ویژگی'),
        ),
        migrations.AlterUniqueTogether(
            name='userfeatureperm',
            unique_together={('user', 'feature', 'custom')},
        ),
    ]
