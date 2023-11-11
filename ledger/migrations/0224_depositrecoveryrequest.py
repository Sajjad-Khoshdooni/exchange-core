# Generated by Django 4.1.3 on 2023-11-01 10:23

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('multimedia', '0023_alter_section_options'),
        ('ledger', '0223_merge_20231023_2005'),
    ]

    operations = [
        migrations.CreateModel(
            name='DepositRecoveryRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('process', 'در حال پردازش'), ('pending', 'در انتظار تایید'), ('canceled', 'لغو شده'), ('done', 'انجام شده')], default='process', max_length=8)),
                ('memo', models.CharField(blank=True, max_length=64)),
                ('trx_hash', models.CharField(max_length=128)),
                ('amount', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('receiver_address', models.CharField(max_length=256)),
                ('sender_address', models.CharField(blank=True, max_length=256)),
                ('description', models.TextField(blank=True)),
                ('comment', models.TextField(blank=True)),
                ('coin', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ledger.asset')),
                ('image', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='multimedia.image', verbose_name='تصویر جزییات برداشت')),
                ('network', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ledger.network')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]