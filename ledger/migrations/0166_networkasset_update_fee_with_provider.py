# Generated by Django 4.1.3 on 2023-02-11 21:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0165_alter_trx_scope'),
    ]

    operations = [
        migrations.AddField(
            model_name='networkasset',
            name='update_fee_with_provider',
            field=models.BooleanField(default=True),
        ),
    ]