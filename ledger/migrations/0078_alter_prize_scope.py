# Generated by Django 4.0 on 2022-05-09 13:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0077_merge_20220502_1155'),
    ]

    operations = [
        migrations.AlterField(
            model_name='prize',
            name='scope',
            field=models.CharField(choices=[('trade_2m', 'trade_2m')], max_length=25, verbose_name='نوع'),
        ),
    ]
