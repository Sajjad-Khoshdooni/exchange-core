# Generated by Django 4.1.3 on 2023-09-09 10:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0141_merge_20230822_1235'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicaluser',
            name='is_price_notif_on',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='is_price_notif_on',
            field=models.BooleanField(default=False),
        ),
    ]
