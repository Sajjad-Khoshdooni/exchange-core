# Generated by Django 4.0 on 2022-04-13 09:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0073_merge_0068_merge_20220404_1125_0072_alter_prize_scope'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Order',
        ),
    ]