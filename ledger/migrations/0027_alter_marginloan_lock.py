# Generated by Django 4.0 on 2022-01-29 09:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0026_alter_marginloan_type_alter_otcrequest_market_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='marginloan',
            name='lock',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='ledger.balancelock'),
        ),
    ]
