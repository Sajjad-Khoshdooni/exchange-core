# Generated by Django 4.1.3 on 2023-07-08 11:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0135_delete_externalnotification'),
        ('market', '0051_remove_pairsymbol_check_market_pairsymbol_amounts_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='cancelrequest',
            name='login_activity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.loginactivity'),
        ),
        migrations.AddField(
            model_name='order',
            name='login_activity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.loginactivity'),
        ),
        migrations.AddField(
            model_name='stoploss',
            name='login_activity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.loginactivity'),
        ),
        migrations.AddField(
            model_name='trade',
            name='login_activity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.loginactivity'),
        ),
    ]