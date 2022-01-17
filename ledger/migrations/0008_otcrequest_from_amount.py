# Generated by Django 4.0 on 2022-01-17 07:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0007_rename_price_otcrequest_to_amount_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='otcrequest',
            name='from_amount',
            field=models.DecimalField(decimal_places=18, default=0, max_digits=40),
            preserve_default=False,
        ),
    ]
