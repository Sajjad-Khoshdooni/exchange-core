# Generated by Django 4.1.3 on 2023-05-06 11:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0175_alter_closerequest_group_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='addresskey',
            name='deleted',
            field=models.BooleanField(default=False),
        ),
        # migrations.AlterUniqueTogether(
        #     name='depositaddress',
        #     unique_together={('network', 'address_key'), ('network', 'address')},
        # ),
        # migrations.AddConstraint(
        #     model_name='addresskey',
        #     constraint=models.UniqueConstraint(condition=models.Q(('deleted', False)), fields=('account', 'architecture'), name='ledger_addresskey_unique_account_architecture'),
        # ),
    ]
