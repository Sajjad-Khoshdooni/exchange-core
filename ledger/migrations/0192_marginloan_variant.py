# Generated by Django 4.1.3 on 2023-07-24 15:05

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0191_marginposition'),
    ]

    operations = [
        migrations.AddField(
            model_name='marginloan',
            name='variant',
            field=models.UUIDField(blank=True, default=uuid.uuid4, null=True),
        ),
    ]
