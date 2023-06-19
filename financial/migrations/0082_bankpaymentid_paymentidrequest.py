# Generated by Django 4.1.3 on 2023-06-01 12:03

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0081_alter_fiatwithdrawrequest_status_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='BankPaymentId',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('destination_deposit_number', models.IntegerField()),
                ('destination_iban', models.CharField(max_length=100)),
                ('merchant_code', models.CharField(max_length=100)),
                ('merchant_name', models.CharField(max_length=100)),
                ('merchant_reference_number', models.IntegerField()),
                ('pay_id', models.IntegerField()),
                ('registry_status', models.CharField(choices=[('WAITING_FOR_USER', 'WAITING_FOR_USER'), ('WAITING_FOR_VERIFICATION', 'WAITING_FOR_VERIFICATION'), ('VERIFIED', 'VERIFIED'), ('REJECTED', 'REJECTED'), ('REVIEWING', 'REVIEWING')], default='WAITING_FOR_VERIFICATION', max_length=28)),
                ('user_iban', models.CharField(max_length=100)),
                ('user_iban_list', models.TextField(null=True)),
                ('bank_account', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='financial.bankaccount')),
                ('gateway', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='financial.gateway')),
            ],
            options={
                'unique_together': {('gateway', 'bank_account')},
            },
        ),
        migrations.CreateModel(
            name='PaymentIdRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('group_id', models.UUIDField(default=uuid.uuid4)),
                ('amount', models.PositiveIntegerField()),
                ('bank', models.CharField(max_length=16)),
                ('bank_reference_number', models.IntegerField()),
                ('destination_account_identifier', models.CharField(max_length=100)),
                ('external_reference_number', models.IntegerField()),
                ('payment_id', models.IntegerField(unique=True)),
                ('raw_bank_timestamp', models.DateTimeField()),
                ('status', models.CharField(choices=[('IN_PROGRESS', 'IN_PROGRESS'), (' WAITING_FOR_MERCHANT_VERIFY', ' WAITING_FOR_MERCHANT_VERIFY'), ('FAILED', 'FAILED'), ('SUCCESSFUL', 'SUCCESSFUL')], default='IN_PROGRESS', max_length=30)),
                ('bank_payment_id', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='financial.bankpaymentid')),
            ],
        ),
    ]