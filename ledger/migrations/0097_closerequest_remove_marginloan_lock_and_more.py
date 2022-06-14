# Generated by Django 4.0 on 2022-06-14 09:39

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0059_remove_account_last_margin_warn_and_more'),
        ('ledger', '0096_remove_asset_precision'),
    ]

    operations = [
        migrations.CreateModel(
            name='CloseRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('group_id', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('margin_level', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('reason', models.CharField(choices=[('liquid', 'liquid'), ('user', 'user')], max_length=8)),
                ('status', models.CharField(choices=[('new', 'new'), ('done', 'done')], default='new', max_length=8)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.account')),
            ],
        ),
        migrations.RemoveField(
            model_name='marginloan',
            name='lock',
        ),
        migrations.AddField(
            model_name='balancelock',
            name='reason',
            field=models.CharField(choices=[('trade', 'trade'), ('withdraw', 'withdraw')], default='', max_length=8),
            preserve_default=False,
        ),
        migrations.DeleteModel(
            name='MarginLiquidation',
        ),
        migrations.AddConstraint(
            model_name='closerequest',
            constraint=models.CheckConstraint(check=models.Q(('margin_level__gte', 0)), name='check_margin_level'),
        ),
    ]
