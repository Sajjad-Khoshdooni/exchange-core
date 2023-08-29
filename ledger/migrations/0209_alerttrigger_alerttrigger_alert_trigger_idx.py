# Generated by Django 4.1.3 on 2023-08-21 14:11

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0208_remove_asset_price_precision_irt_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlertTrigger',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('price', models.DecimalField(decimal_places=8, max_digits=30, validators=[django.core.validators.MinValueValidator(0)])),
                ('cycle', models.PositiveIntegerField()),
                ('interval', models.CharField(choices=[('5m', 'پنج\u200c دقیقه'), ('1h', '\u200cیک\u200c ساعت')], max_length=15)),
                ('is_triggered', models.BooleanField(default=False)),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ledger.asset')),
            ],
        ),
        migrations.AddIndex(
            model_name='alerttrigger',
            index=models.Index(fields=['is_triggered', 'asset', 'created'], name='alert_trigger_idx'),
        ),
    ]
