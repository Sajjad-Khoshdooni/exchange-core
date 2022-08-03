# Generated by Django 4.0 on 2022-08-03 07:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0116_merge_20220803_1056'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transfer',
            name='source',
            field=models.CharField(choices=[('self', 'self'), ('binance', 'binance'), ('internal', 'internal')], default='self', max_length=8),
        ),
    ]
