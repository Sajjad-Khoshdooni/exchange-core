# Generated by Django 4.1.3 on 2023-09-12 12:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0148_forget2fa'),
    ]

    operations = [
        migrations.AlterField(
            model_name='verificationcode',
            name='scope',
            field=models.CharField(choices=[('forget', 'forget'), ('verify', 'verify'), ('withdraw', 'withdraw'), ('tel', 'tel'), ('change_pass', 'change_pass'), ('change_phone', 'change_phone'), ('change_phone_v1', 'change_phone_v1'), ('email_verify', 'email_verify'), ('fiat_withdraw', 'fiat_withdraw'), ('2fa', '2fa'), ('api_token', 'api_token'), ('address_book', 'address_book')], db_index=True, max_length=32),
        ),
    ]
