# Generated by Django 4.1.3 on 2023-06-30 08:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0090_gateway_ipg_fee_max_gateway_ipg_fee_min_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gateway',
            name='type',
            field=models.CharField(choices=[('manual', 'manual'), ('zarinpal', 'zarinpal'), ('payir', 'payir'), ('zibal', 'zibal'), ('jibit', 'jibit'), ('jibimo', 'jibimo')], max_length=8),
        ),
    ]
