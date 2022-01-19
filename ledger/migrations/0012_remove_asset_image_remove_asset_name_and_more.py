# Generated by Django 4.0 on 2022-01-19 08:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0011_alter_balancelock_release_date'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='asset',
            name='image',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='name',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='name_fa',
        ),
        migrations.RemoveField(
            model_name='network',
            name='name',
        ),
        migrations.RemoveField(
            model_name='network',
            name='name_fa',
        ),
        migrations.AlterField(
            model_name='asset',
            name='symbol',
            field=models.CharField(db_index=True, max_length=8, unique=True),
        ),
    ]
