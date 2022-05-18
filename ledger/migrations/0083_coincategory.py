# Generated by Django 4.0 on 2022-05-17 10:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0082_alter_networkasset_withdraw_fee_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CoinCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30)),
                ('name_fa', models.CharField(blank=True, max_length=30, null=True)),
                ('coin', models.ManyToManyField(blank=True, null=True, to='ledger.Asset')),
            ],
        ),
    ]
