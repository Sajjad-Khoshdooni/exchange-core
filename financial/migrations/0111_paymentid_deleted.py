# Generated by Django 4.1.3 on 2024-01-14 15:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0110_gateway_suspended'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentid',
            name='deleted',
            field=models.BooleanField(default=False),
        ),
    ]