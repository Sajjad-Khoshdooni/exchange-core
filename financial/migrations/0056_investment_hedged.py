# Generated by Django 4.0 on 2022-08-18 06:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0055_investment_invested'),
    ]

    operations = [
        migrations.AddField(
            model_name='investment',
            name='hedged',
            field=models.BooleanField(default=False),
        ),
    ]
