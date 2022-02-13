# Generated by Django 4.0 on 2022-02-08 09:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0044_transfer_fee_amount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trx',
            name='scope',
            field=models.CharField(choices=[('t', 'trade'), ('f', 'transfer'), ('m', 'margin transfer'), ('b', 'margin borrow'), ('c', 'commission')], max_length=1),
        ),
    ]