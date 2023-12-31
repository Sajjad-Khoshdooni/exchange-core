# Generated by Django 4.1.3 on 2023-12-28 10:24

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0174_remove_systemconfig_mean_leverage_and_more'),
        ('ledger', '0232_alter_marginleverage_leverage_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='marginleverage',
            name='account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.account', unique=True),
        ),
    ]