# Generated by Django 4.0 on 2022-06-06 10:59

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0057_alter_account_bookmark_assets_and_more'),
        ('market', '0021_order_check_filled_amount'),
    ]

    operations = [
        migrations.CreateModel(
            name='Trade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField()),
                ('side', models.CharField(choices=[('buy', 'buy'), ('sell', 'sell')], max_length=8)),
                ('amount', models.DecimalField(decimal_places=18, max_digits=40, validators=[django.core.validators.MinValueValidator(0)])),
                ('price', models.DecimalField(decimal_places=18, max_digits=40, validators=[django.core.validators.MinValueValidator(0)])),
                ('is_maker', models.BooleanField()),
                ('group_id', models.UUIDField(default=uuid.uuid4, editable=False)),
                ('base_amount', models.DecimalField(decimal_places=18, max_digits=40, validators=[django.core.validators.MinValueValidator(0)])),
                ('fee_amount', models.DecimalField(decimal_places=18, max_digits=40, validators=[django.core.validators.MinValueValidator(0)])),
                ('irt_value', models.PositiveIntegerField()),
                ('trade_source', models.CharField(choices=[('otc', 'otc'), ('market', 'market'), ('system', 'system')], db_index=True, default='market', max_length=8)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='accounts.account')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trades', to='market.order')),
                ('symbol', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='market.pairsymbol')),
            ],
        ),
        migrations.AddIndex(
            model_name='trade',
            index=models.Index(fields=['account', 'symbol'], name='market_trad_account_ac402e_idx'),
        ),
        migrations.AddIndex(
            model_name='trade',
            index=models.Index(fields=['symbol', 'side', 'created'], name='market_trad_symbol__9eefff_idx'),
        ),
    ]
