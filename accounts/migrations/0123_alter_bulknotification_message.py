# Generated by Django 4.1.3 on 2023-06-07 14:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0122_historicaluser_can_withdraw_crypto_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bulknotification',
            name='message',
            field=models.TextField(blank=True),
        ),
    ]