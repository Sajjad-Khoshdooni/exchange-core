# Generated by Django 4.0 on 2022-02-13 13:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0046_cryptobalance'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='trx',
            unique_together={('group_id', 'sender', 'receiver', 'scope')},
        ),
    ]
