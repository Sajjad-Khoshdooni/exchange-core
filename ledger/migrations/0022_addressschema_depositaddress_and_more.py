# Generated by Django 4.0 on 2022-01-26 11:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_account_type'),
        ('ledger', '0021_trx_scope_alter_wallet_market_margintransfer_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AddressSchema',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symbol', models.CharField(max_length=4, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='DepositAddress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.CharField(blank=True, max_length=256, unique=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='accounts.account')),
                ('schema', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='ledger.addressschema')),
            ],
            options={
                'unique_together': {('schema', 'account')},
            },
        ),
        migrations.RenameField(
            model_name='networkasset',
            old_name='min_transfer',
            new_name='min_withdraw',
        ),
        migrations.RenameField(
            model_name='networkasset',
            old_name='commission',
            new_name='withdraw_commission',
        ),
        migrations.RemoveField(
            model_name='transfer',
            name='network_address',
        ),
        migrations.AddField(
            model_name='network',
            name='can_deposit',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='network',
            name='can_withdraw',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='otcrequest',
            name='from_asset',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='from_otc_requests', to='ledger.asset'),
        ),
        migrations.AlterField(
            model_name='otcrequest',
            name='to_asset',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='to_otc_requests', to='ledger.asset'),
        ),
        migrations.DeleteModel(
            name='NetworkAddress',
        ),
        migrations.AddField(
            model_name='network',
            name='schema',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.PROTECT, to='ledger.addressschema'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transfer',
            name='deposit_address',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='ledger.depositaddress'),
            preserve_default=False,
        ),
    ]
