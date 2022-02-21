# Generated by Django 4.0 on 2022-02-21 07:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0054_remove_asset_withdraw_step_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='marginloan',
            name='lock',
            field=models.OneToOneField(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='ledger.balancelock'),
        ),
        migrations.AlterField(
            model_name='otctrade',
            name='lock',
            field=models.OneToOneField(editable=False, on_delete=django.db.models.deletion.CASCADE, to='ledger.balancelock'),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='trx_hash',
            field=models.CharField(blank=True, db_index=True, max_length=128, null=True),
        ),
    ]
