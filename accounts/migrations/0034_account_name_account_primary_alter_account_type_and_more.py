# Generated by Django 4.0 on 2022-04-13 09:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0033_merge_20220409_1800'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='name',
            field=models.CharField(blank=True, max_length=16),
        ),
        migrations.AddField(
            model_name='account',
            name='primary',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='account',
            name='type',
            field=models.CharField(blank=True, choices=[('s', 'system'), ('o', 'out'), (None, 'ordinary')], max_length=1, null=True),
        ),
        migrations.AddConstraint(
            model_name='account',
            constraint=models.UniqueConstraint(condition=models.Q(('primary', True)), fields=('type',), name='unique_account_type_primary'),
        ),
    ]
