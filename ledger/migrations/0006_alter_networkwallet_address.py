# Generated by Django 4.0 on 2022-01-04 09:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0005_alter_balancelock_amount_alter_order_amount_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='networkwallet',
            name='address',
            field=models.CharField(db_index=True, max_length=256),
        ),
    ]
