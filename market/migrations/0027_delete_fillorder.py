# Generated by Django 4.0 on 2022-06-27 10:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0026_merge_20220622_1003'),
    ]

    operations = [
        migrations.DeleteModel(
            name='FillOrder',
        ),
    ]
