# Generated by Django 4.1.3 on 2023-09-23 08:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0147_rename_consultation_consultee_consultation_user_and_more'),
        ('ledger', '0216_merge_20230911_1209'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='addresskey',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='addresskey',
            name='memo',
            field=models.CharField(blank=True, max_length=256),
        ),
        migrations.AlterUniqueTogether(
            name='addresskey',
            unique_together={('account', 'address', 'memo')},
        ),
        migrations.AlterUniqueTogether(
            name='depositaddress',
            unique_together={('address_key', 'network', 'address')},
        ),
        migrations.AddConstraint(
            model_name='addresskey',
            constraint=models.UniqueConstraint(condition=models.Q(('mamo__isnull', False)), fields=('memo', 'architecture'), name='ledger_addresskey_unique_memo_architecture'),
        ),
    ]
