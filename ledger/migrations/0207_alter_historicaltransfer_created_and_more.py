# Generated by Django 4.1.3 on 2023-08-19 12:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0206_alter_systemsnapshot_cum_hedge_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicaltransfer',
            name='created',
            field=models.DateTimeField(blank=True, db_index=True, editable=False),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='created',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
    ]