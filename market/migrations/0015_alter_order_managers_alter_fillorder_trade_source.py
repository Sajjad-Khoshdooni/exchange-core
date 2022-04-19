# Generated by Django 4.0 on 2022-04-19 06:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0014_alter_order_filled_amount'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='order',
            managers=[
            ],
        ),
        migrations.AlterField(
            model_name='fillorder',
            name='trade_source',
            field=models.CharField(choices=[('otc', 'otc'), ('market', 'market'), ('system', 'system')], db_index=True, default='market', max_length=8),
        ),
    ]
