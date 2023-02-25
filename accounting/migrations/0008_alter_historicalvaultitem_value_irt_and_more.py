# Generated by Django 4.1.3 on 2023-02-21 17:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0007_historicalreservedasset_value_irt_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalvaultitem',
            name='value_irt',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=30),
        ),
        migrations.AlterField(
            model_name='historicalvaultitem',
            name='value_usdt',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=30),
        ),
        migrations.AlterField(
            model_name='vaultitem',
            name='value_irt',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=30),
        ),
        migrations.AlterField(
            model_name='vaultitem',
            name='value_usdt',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=30),
        ),
    ]