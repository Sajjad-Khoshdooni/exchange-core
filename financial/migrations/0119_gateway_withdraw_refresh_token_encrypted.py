# Generated by Django 4.1.3 on 2024-01-24 12:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0118_remove_gateway_withdraw_bank'),
    ]

    operations = [
        migrations.AddField(
            model_name='gateway',
            name='withdraw_refresh_token_encrypted',
            field=models.CharField(blank=True, max_length=4096),
        ),
    ]
