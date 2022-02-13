# Generated by Django 4.0 on 2022-02-13 08:15

import accounts.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_account_last_margin_warn'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='verification',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.CreateModel(
            name='BasicAccountInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('verifier_code', models.CharField(blank=True, max_length=16)),
                ('status', models.CharField(choices=[('init', 'init'), ('pending', 'pending'), ('rejected', 'rejected'), ('verified', 'verified')], default='init', max_length=8)),
                ('gender', models.CharField(choices=[('m', 'm'), ('f', 'f')], max_length=1)),
                ('birth_date', models.DateField()),
                ('national_card_code', models.CharField(max_length=10, validators=[accounts.validators.national_card_code_validator])),
                ('national_card_image', models.ImageField(upload_to='')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to='accounts.user')),
            ],
        ),
        migrations.CreateModel(
            name='BankCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=256)),
                ('card_number', models.CharField(max_length=20, unique=True, validators=[accounts.validators.bank_card_pan_validator], verbose_name='شماره کارت')),
                ('iban', models.CharField(max_length=26, unique=True, validators=[accounts.validators.iban_validator], verbose_name='شبا')),
                ('verified', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='accounts.user')),
            ],
            options={
                'verbose_name': 'کارت بانکی',
                'verbose_name_plural': 'کارت\u200cهای بانکی',
            },
        ),
    ]
