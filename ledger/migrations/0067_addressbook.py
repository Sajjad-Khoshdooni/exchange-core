# Generated by Django 4.0 on 2022-03-30 07:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0021_alter_finotechrequest_created_and_more'),
        ('ledger', '0066_otcrequest_to_price_absolute_usdt'),
    ]

    operations = [
        migrations.CreateModel(
            name='AddressBook',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.account')),
                ('asset', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='ledger.asset')),
                ('network', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ledger.network')),
            ],
        ),
    ]
