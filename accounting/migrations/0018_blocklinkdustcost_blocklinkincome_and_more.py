# Generated by Django 4.0 on 2023-03-06 14:23

from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0102_historicaluser_first_crypto_deposit_date_and_more'),
        ('accounting', '0017_periodicfetcher_providerincome'),
    ]

    operations = [
        migrations.CreateModel(
            name='BlocklinkDustCost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('updated', models.DateTimeField(auto_now=True)),
                ('amount', models.PositiveIntegerField()),
                ('usdt_value', models.PositiveIntegerField()),
                ('network', models.CharField(max_length=16)),
                ('coin', models.CharField(max_length=16)),
            ],
        ),
        migrations.CreateModel(
            name='BlockLinkIncome',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('start', models.DateTimeField(unique=True)),
                ('real_fee_amount', models.PositiveIntegerField()),
                ('fee_cost', models.PositiveIntegerField()),
                ('fee_income', models.PositiveIntegerField()),
                ('network', models.CharField(max_length=16)),
                ('coin', models.CharField(max_length=16)),
            ],
        ),
        migrations.CreateModel(
            name='HistoricalBlocklinkDustCost',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('updated', models.DateTimeField(blank=True, editable=False)),
                ('amount', models.PositiveIntegerField()),
                ('usdt_value', models.PositiveIntegerField()),
                ('network', models.CharField(max_length=16)),
                ('coin', models.CharField(max_length=16)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='accounts.user')),
            ],
            options={
                'verbose_name': 'historical blocklink dust cost',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]