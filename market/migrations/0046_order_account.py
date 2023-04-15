# Generated by Django 4.1.3 on 2023-03-16 08:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0105_merge_20230314_1509'),
        ('market', '0045_alter_order_time_in_force'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='accounts.account', null=True),
            preserve_default=False,
        ),
        # migrations.RunSQL(
        #     sql='UPDATE market_order o SET account_id = w.account_id FROM ledger_wallet w WHERE o.wallet_id = w.id;',
        #     reverse_sql=migrations.RunSQL.noop
        # ),
        # migrations.AlterField(
        #     model_name='order',
        #     name='account',
        #     field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='accounts.account'),
        # ),
    ]
