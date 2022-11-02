# Generated by Django 4.0 on 2022-06-29 07:41

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0063_alter_externalnotification_options_and_more'),
        ('ledger', '0100_system_balance_populate'),
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
        migrations.AddField(
            model_name='balancelock',
            name='reason',
            field=models.CharField(blank=True, max_length=8, null=True),
        ),
        migrations.DeleteModel(
            name='MarginLiquidation',
        ),
        migrations.AddConstraint(
            model_name='closerequest',
            constraint=models.CheckConstraint(check=models.Q(('margin_level__gte', 0)), name='check_margin_level'),
        ),
        migrations.AddConstraint(
            model_name='closerequest',
            constraint=models.UniqueConstraint(condition=models.Q(('status', 'new')), fields=('account',), name='unique_margin_close_request_account'),
        ),
    ]