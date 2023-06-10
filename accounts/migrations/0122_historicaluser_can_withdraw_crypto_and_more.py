# Generated by Django 4.1.3 on 2023-06-06 12:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0121_merge_20230523_1359'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicaluser',
            name='can_withdraw_crypto',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='user',
            name='can_withdraw_crypto',
            field=models.BooleanField(default=True),
        ),
    ]
