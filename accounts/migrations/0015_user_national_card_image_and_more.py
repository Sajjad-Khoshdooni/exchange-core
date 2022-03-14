# Generated by Django 4.0 on 2022-03-06 10:32

import accounts.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('multimedia', '0001_initial'),
        ('accounts', '0014_user_first_fiat_deposit_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='national_card_image',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='multimedia.image', verbose_name='عکس کارت ملی'),
        ),
        migrations.AddField(
            model_name='user',
            name='national_card_image_verified',
            field=models.BooleanField(blank=True, null=True, verbose_name='تاییدیه عکس کارت ملی'),
        ),
        migrations.AddField(
            model_name='user',
            name='selfie_image',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='multimedia.image', verbose_name='عکس سلفی'),
        ),
        migrations.AddField(
            model_name='user',
            name='selfie_image_verified',
            field=models.BooleanField(blank=True, null=True, verbose_name='تاییدیه عکس سلفی'),
        ),
        migrations.AddField(
            model_name='user',
            name='telephone',
            field=models.CharField(blank=True, error_messages={'unique': 'شماره موبایل وارد شده از قبل در سیستم موجود است.'}, max_length=16, null=True, unique=True, validators=[accounts.validators.telephone_number_validator], verbose_name='شماره تلفن'),
        ),
        migrations.AddField(
            model_name='user',
            name='telephone_verified',
            field=models.BooleanField(blank=True, null=True, verbose_name='تاییدیه شماره تلفن'),
        ),
        migrations.AlterField(
            model_name='user',
            name='birth_date',
            field=models.DateField(blank=True, null=True, verbose_name='تاریخ تولد'),
        ),
        migrations.AlterField(
            model_name='user',
            name='birth_date_verified',
            field=models.BooleanField(blank=True, null=True, verbose_name='تاییدیه تاریخ تولد'),
        ),
        migrations.AlterField(
            model_name='user',
            name='email_verified',
            field=models.BooleanField(default=False, verbose_name='تاییدیه ایمیل'),
        ),
        migrations.AlterField(
            model_name='user',
            name='first_fiat_deposit_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='زمان اولین برداشت ریالی'),
        ),
        migrations.AlterField(
            model_name='user',
            name='first_name_verified',
            field=models.BooleanField(blank=True, null=True, verbose_name='تاییدیه نام'),
        ),
        migrations.AlterField(
            model_name='user',
            name='last_name_verified',
            field=models.BooleanField(blank=True, null=True, verbose_name='تاییدیه نام خانوادگی'),
        ),
        migrations.AlterField(
            model_name='user',
            name='level',
            field=models.PositiveSmallIntegerField(choices=[(1, 'level 1'), (2, 'level 2'), (3, 'level 3')], default=1, verbose_name='سطح'),
        ),
        migrations.AlterField(
            model_name='user',
            name='national_code',
            field=models.CharField(blank=True, max_length=10, validators=[accounts.validators.national_card_code_validator], verbose_name='کد ملی'),
        ),
        migrations.AlterField(
            model_name='user',
            name='national_code_verified',
            field=models.BooleanField(blank=True, null=True, verbose_name='تاییدیه کد ملی'),
        ),
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(db_index=True, error_messages={'unique': 'شماره موبایل وارد شده از قبل در سیستم موجود است.'}, max_length=16, unique=True, validators=[accounts.validators.mobile_number_validator], verbose_name='شماره موبایل'),
        ),
        migrations.AlterField(
            model_name='user',
            name='verify_status',
            field=models.CharField(choices=[('init', 'init'), ('pending', 'pending'), ('rejected', 'rejected'), ('verified', 'verified')], default='init', max_length=8, verbose_name='وضعیت تایید'),
        ),
        migrations.AlterField(
            model_name='verificationcode',
            name='phone',
            field=models.CharField(db_index=True, max_length=16, verbose_name='شماره تماس'),
        ),
        migrations.AlterField(
            model_name='verificationcode',
            name='scope',
            field=models.CharField(choices=[('forget', 'forget'), ('verify', 'verify'), ('withdraw', 'withdraw'), ('tel', 'tel')], max_length=8),
        ),
    ]