# Generated by Django 4.1.3 on 2023-05-03 12:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0079_manualtransfer_bankaccount_stake_holder_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='manualtransfer',
            name='amount',
            field=models.PositiveIntegerField(),
        ),
    ]