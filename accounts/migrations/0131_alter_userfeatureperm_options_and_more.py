# Generated by Django 4.1.3 on 2023-06-20 07:51

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0130_userfeatureperm_limit_alter_userfeatureperm_feature'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='userfeatureperm',
            options={'verbose_name': 'دسترسی\u200c کاربر', 'verbose_name_plural': 'دسترسی\u200cهای کاربر'},
        ),
        migrations.AlterField(
            model_name='userfeatureperm',
            name='feature',
            field=models.CharField(choices=[('pay_id', 'pay_id'), ('fiat_deposit_limit', 'fiat_deposit_limit')], max_length=32, verbose_name='ویژگی'),
        ),
        migrations.AlterField(
            model_name='userfeatureperm',
            name='limit',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=30, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='محدودیت'),
        ),
        migrations.AlterField(
            model_name='userfeatureperm',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='کاربر'),
        ),
    ]