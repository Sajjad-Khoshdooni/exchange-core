# Generated by Django 4.0 on 2022-08-31 14:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0119_remove_depositaddress_is_registered'),
        ('ledger', '0133_merge_20220831_1216'),
    ]

    operations = [
        migrations.AlterField(
            model_name='addresskey',
            name='public_address',
            field=models.CharField(max_length=256),
            preserve_default=False,
        ),
    ]
