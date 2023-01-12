# Generated by Django 4.1.3 on 2023-01-12 14:43

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0034_trade_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trade',
            name='group_id',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False),
        ),
    ]