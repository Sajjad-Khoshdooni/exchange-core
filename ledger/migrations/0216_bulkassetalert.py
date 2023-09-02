# Generated by Django 4.1.3 on 2023-09-02 12:55

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ledger', '0215_alerttrigger_chanel_alerttrigger_is_chanel_changed_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='BulkAssetAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('subscription_type', models.CharField(choices=[('my_assets', 'my_assets'), ('all_coins', 'all_coins'), ('asset_categories', 'asset_categories')], max_length=20)),
                ('coin_category', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='ledger.coincategory')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'subscription_type', 'coin_category')},
            },
        ),
    ]
