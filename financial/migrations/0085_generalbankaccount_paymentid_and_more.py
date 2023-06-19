# Generated by Django 4.1.3 on 2023-06-12 16:37

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import financial.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('financial', '0084_gateway_primary_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='GeneralBankAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('iban', models.CharField(max_length=26, unique=True, validators=[financial.validators.iban_validator], verbose_name='شبا')),
                ('name', models.CharField(blank=True, max_length=256)),
                ('bank', models.CharField(blank=True, max_length=256)),
                ('deposit_address', models.CharField(blank=True, max_length=64)),
            ],
        ),
        migrations.CreateModel(
            name='PaymentId',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('pay_id', models.CharField(max_length=32, validators=[django.core.validators.validate_integer])),
                ('verified', models.BooleanField(default=False)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='bankpaymentid',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='bankpaymentid',
            name='bank_account',
        ),
        migrations.RemoveField(
            model_name='bankpaymentid',
            name='gateway',
        ),
        migrations.RemoveField(
            model_name='paymentidrequest',
            name='bank',
        ),
        migrations.RemoveField(
            model_name='paymentidrequest',
            name='bank_payment_id',
        ),
        migrations.RemoveField(
            model_name='paymentidrequest',
            name='bank_reference_number',
        ),
        migrations.RemoveField(
            model_name='paymentidrequest',
            name='destination_account_identifier',
        ),
        migrations.RemoveField(
            model_name='paymentidrequest',
            name='external_reference_number',
        ),
        migrations.RemoveField(
            model_name='paymentidrequest',
            name='group_id',
        ),
        migrations.RemoveField(
            model_name='paymentidrequest',
            name='modified',
        ),
        migrations.RemoveField(
            model_name='paymentidrequest',
            name='raw_bank_timestamp',
        ),
        migrations.AddField(
            model_name='payment',
            name='payment_id_request',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='financial.paymentidrequest'),
        ),
        migrations.AddField(
            model_name='paymentidrequest',
            name='bank_ref',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='paymentidrequest',
            name='external_ref',
            field=models.CharField(blank=True, max_length=64, unique=True),
        ),
        migrations.AddField(
            model_name='paymentidrequest',
            name='source_iban',
            field=models.CharField(default='', max_length=26, unique=True, validators=[financial.validators.iban_validator], verbose_name='شبا'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='payment',
            name='payment_request',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='financial.paymentrequest'),
        ),
        migrations.AlterField(
            model_name='payment',
            name='status',
            field=models.CharField(choices=[('process', 'در حال پردازش'), ('pending', 'در انتظار تایید'), ('canceled', 'لغو شده'), ('done', 'انجام شده')], default='pending', max_length=8),
        ),
        migrations.AlterField(
            model_name='paymentidrequest',
            name='status',
            field=models.CharField(choices=[('process', 'در حال پردازش'), ('pending', 'در انتظار تایید'), ('canceled', 'لغو شده'), ('done', 'انجام شده')], default='pending', max_length=8),
        ),
        migrations.AddConstraint(
            model_name='payment',
            constraint=models.CheckConstraint(check=models.Q(models.Q(('payment_id_request__isnull', True), ('payment_request__isnull', False)), models.Q(('payment_id_request__isnull', False), ('payment_request__isnull', True)), _connector='OR'), name='check_financial_payment_requests'),
        ),
        migrations.DeleteModel(
            name='BankPaymentId',
        ),
        migrations.AddField(
            model_name='paymentid',
            name='destination',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='financial.generalbankaccount'),
        ),
        migrations.AddField(
            model_name='paymentid',
            name='gateway',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='financial.gateway'),
        ),
        migrations.AddField(
            model_name='paymentid',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='paymentidrequest',
            name='payment_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='financial.paymentid'),
        ),
        migrations.AlterUniqueTogether(
            name='paymentid',
            unique_together={('pay_id', 'gateway'), ('user', 'gateway')},
        ),
    ]