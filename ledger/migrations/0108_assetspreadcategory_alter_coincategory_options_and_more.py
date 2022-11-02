# Generated by Django 4.0 on 2022-07-26 11:15

from decimal import Decimal
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0107_alter_wallet_balance'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssetSpreadCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, unique=True)),
            ],
        ),
        migrations.AlterModelOptions(
            name='coincategory',
            options={'verbose_name': 'گروه\u200cبندی نمایش رمزارزها', 'verbose_name_plural': 'گروه\u200cبندی نمایش رمزارزها'},
        ),
        migrations.RemoveField(
            model_name='asset',
            name='ask_diff',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='bid_diff',
        ),
        migrations.AlterField(
            model_name='coincategory',
            name='name',
            field=models.CharField(db_index=True, max_length=32),
        ),
        migrations.AddField(
            model_name='asset',
            name='spread_category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='ledger.assetspreadcategory'),
        ),
        migrations.CreateModel(
            name='CategorySpread',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('side', models.CharField(choices=[('buy', 'buy'), ('sell', 'sell')], max_length=8)),
                ('step', models.PositiveIntegerField(choices=[(1, '0$ - 3$'), (2, '3$ - 10$'), (3, '10$ - 1000$'), (4, '> 1000$')], validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(4)])),
                ('spread', models.DecimalField(decimal_places=8, default=Decimal('0.25'), max_digits=30, validators=[django.core.validators.MinValueValidator(Decimal('0.1')), django.core.validators.MaxValueValidator(15)])),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='ledger.assetspreadcategory')),
            ],
            options={
                'unique_together': {('category', 'side', 'step')},
            },
        ),
    ]