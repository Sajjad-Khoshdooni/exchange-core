# Generated by Django 4.0 on 2022-06-08 12:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0023_populate_trades'),
    ]

    operations = [
        migrations.DeleteModel(
            name='FillOrder',
        ),
    ]
