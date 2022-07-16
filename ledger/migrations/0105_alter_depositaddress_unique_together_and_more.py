# Generated by Django 4.0 on 2022-07-09 08:59
import base58
import django.utils.timezone
from django.db import migrations, models


def populate_address_key(apps, schema_editor):
    AddressKey = apps.get_model('ledger', 'AddressKey')
    DepositAddress = apps.get_model('ledger', 'DepositAddress')

    for deposit_address in DepositAddress.objects.all():
        account_secret = deposit_address.account_secret

        address = deposit_address.address

        if address.startswith('41'):
            address_key = '0x' + address[2:]
            address = base58.b58encode_check(bytes.fromhex(address)).decode()
        else:
            address_key = address

        deposit_address.address_key = AddressKey.objects.create(
            account=account_secret.account,
            address=address_key
        )
        deposit_address.address = address
        deposit_address.save()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0064_alter_externalnotification_scope'),
        ('ledger', '0104_network_need_memo_transfer_memo'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='depositaddress',
            unique_together={('network', 'address')},
        ),
        migrations.AddField(
            model_name='depositaddress',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='depositaddress',
            name='is_registered',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='AddressKey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.CharField(max_length=256)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='accounts.account')),
            ],
            options={
                'unique_together': {('account', 'address')},
            },
        ),
        migrations.AddField(
            model_name='depositaddress',
            name='address_key',
            field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to='ledger.addresskey', null=True),
            preserve_default=False,
        ),

        migrations.RunPython(code=populate_address_key, reverse_code=migrations.RunPython.noop),

        migrations.AlterField(
            model_name='depositaddress',
            name='address_key',
            field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to='ledger.addresskey'),
            preserve_default=False,
        ),
    ]
