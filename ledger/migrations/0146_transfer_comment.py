# Generated by Django 4.1.3 on 2022-12-12 08:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0145_remove_transfer_handling'),
    ]

    operations = [
        migrations.AddField(
            model_name='transfer',
            name='comment',
            field=models.TextField(blank=True, verbose_name='نظر'),
        ),
    ]
