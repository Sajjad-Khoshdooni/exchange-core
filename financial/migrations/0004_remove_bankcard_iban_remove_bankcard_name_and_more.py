# Generated by Django 4.0 on 2022-02-15 06:21

from django.db import migrations, models
import django.db.models.deletion
import financial.validators


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_delete_bankcard'),
        ('financial', '0003_bankcard_alter_paymentrequest_bank_card'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bankcard',
            name='iban',
        ),
        migrations.RemoveField(
            model_name='bankcard',
            name='name',
        ),
        migrations.CreateModel(
            name='BankAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('iban', models.CharField(max_length=26, unique=True, validators=[financial.validators.iban_validator], verbose_name='شبا')),
                ('verified', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='accounts.user')),
            ],
            options={
                'verbose_name': 'حساب بانکی',
                'verbose_name_plural': 'حساب\u200cهای بانکی',
            },
        ),
    ]