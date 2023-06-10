# Generated by Django 4.1.3 on 2023-04-05 07:19

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models
import tinymce.models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0175_alter_closerequest_group_id_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('multimedia', '0007_banner_limit'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalCoinPriceContent',
            fields=[
                ('id', models.BigIntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('content', tinymce.models.HTMLField()),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('asset', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='ledger.asset')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical coin price content',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
