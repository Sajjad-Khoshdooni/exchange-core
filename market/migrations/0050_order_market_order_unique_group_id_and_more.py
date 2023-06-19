# Generated by Django 4.1.3 on 2023-05-29 05:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0049_alter_order_unique_together_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='order',
            constraint=models.UniqueConstraint(fields=('group_id', 'status'), name='market_order_unique_group_id'),
        ),
        migrations.AddConstraint(
            model_name='order',
            constraint=models.UniqueConstraint(fields=('stop_loss', 'status'), name='market_order_unique_stop_loss'),
        ),
    ]