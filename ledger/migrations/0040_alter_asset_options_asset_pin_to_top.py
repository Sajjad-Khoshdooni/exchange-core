# Generated by Django 4.0 on 2022-02-06 12:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0039_transfer_provider_transfer_transfer_source_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='asset',
            options={'ordering': ('-pin_to_top', '-trend', 'order')},
        ),
        migrations.AddField(
            model_name='asset',
            name='pin_to_top',
            field=models.BooleanField(default=False),
        ),
    ]