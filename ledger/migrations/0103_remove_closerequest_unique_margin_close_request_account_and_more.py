# Generated by Django 4.0 on 2022-07-02 11:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0102_merge_20220629_1826'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='closerequest',
            name='unique_margin_close_request_account',
        ),
        migrations.AddField(
            model_name='asset',
            name='name',
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name='asset',
            name='name_fa',
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AlterField(
            model_name='closerequest',
            name='status',
            field=models.CharField(choices=[('pending', 'در انتظار تایید'), ('canceled', 'لغو شده'), ('done', 'انجام شده')], default='pending', max_length=8),
        ),
        migrations.AddConstraint(
            model_name='closerequest',
            constraint=models.UniqueConstraint(condition=models.Q(('status', 'pending')), fields=('account',), name='unique_margin_close_request_account'),
        ),
    ]