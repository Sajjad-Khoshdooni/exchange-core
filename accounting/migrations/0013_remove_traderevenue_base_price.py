# Generated by Django 4.1.3 on 2023-02-28 16:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0012_traderevenue_gap_revenue'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='traderevenue',
            name='base_price',
        ),
    ]