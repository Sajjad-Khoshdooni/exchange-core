# Generated by Django 4.0 on 2022-06-13 14:15

from decimal import Decimal
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0021_order_check_filled_amount'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='order',
            name='check_filled_amount'
        ),
        migrations.AlterField(
            model_name='fillorder',
            name='amount',
            field=models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='fillorder',
            name='base_amount',
            field=models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='fillorder',
            name='maker_fee_amount',
            field=models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='fillorder',
            name='price',
            field=models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='fillorder',
            name='taker_fee_amount',
            field=models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='order',
            name='filled_amount',
            field=models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='order',
            name='amount',
            field=models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='order',
            name='price',
            field=models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='pairsymbol',
            name='maker_amount',
            field=models.DecimalField(decimal_places=8, default=Decimal('1'), max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='pairsymbol',
            name='max_trade_quantity',
            field=models.DecimalField(decimal_places=8, default=Decimal('10000'), max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='pairsymbol',
            name='min_trade_quantity',
            field=models.DecimalField(decimal_places=8, default=Decimal('0.0001'), max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='referraltrx',
            name='referrer_amount',
            field=models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='referraltrx',
            name='trader_amount',
            field=models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='stoploss',
            name='amount',
            field=models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='stoploss',
            name='filled_amount',
            field=models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='stoploss',
            name='price',
            field=models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddConstraint(
            model_name='fillorder',
            constraint=models.CheckConstraint(check=models.Q(('amount__gte', 0), ('base_amount__gte', 0), ('maker_fee_amount__gte', 0), ('price__gte', 0), ('taker_fee_amount__gte', 0)), name='check_market_fillorder_amounts'),
        ),
        migrations.AddConstraint(
            model_name='order',
            constraint=models.CheckConstraint(check=models.Q(('amount__gte', 0), ('filled_amount__gte', 0), ('price__gte', 0)), name='check_market_order_amounts'),
        ),
        migrations.AddConstraint(
            model_name='pairsymbol',
            constraint=models.CheckConstraint(check=models.Q(('maker_amount__gte', 0), ('max_trade_quantity__gte', 0), ('min_trade_quantity__gte', 0)), name='check_market_pairsymbol_amounts'),
        ),
        migrations.AddConstraint(
            model_name='referraltrx',
            constraint=models.CheckConstraint(check=models.Q(('referrer_amount__gte', 0), ('trader_amount__gte', 0)), name='check_market_referraltrx_amounts'),
        ),
        migrations.AddConstraint(
            model_name='stoploss',
            constraint=models.CheckConstraint(check=models.Q(('amount__gte', 0), ('filled_amount__gte', 0), ('price__gte', 0)), name='check_market_stoploss_amounts'),
        ),
        migrations.AddConstraint(
            model_name='order',
            constraint=models.CheckConstraint(
                check=models.Q(('filled_amount__lte', django.db.models.expressions.F('amount'))),
                name='check_filled_amount'),
        ),
    ]
