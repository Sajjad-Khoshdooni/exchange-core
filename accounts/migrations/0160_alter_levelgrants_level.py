# Generated by Django 4.1.3 on 2023-10-30 13:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0159_levelgrants_historicaluser_custom_fiat_withdraw_ceil_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='levelgrants',
            name='level',
            field=models.PositiveSmallIntegerField(choices=[(1, 'level 1'), (2, 'level 2'), (3, 'level 3'), (4, 'level 4')], default=1, unique=True, verbose_name='سطح'),
        ),
    ]