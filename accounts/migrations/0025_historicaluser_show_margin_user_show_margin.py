# Generated by Django 4.0 on 2022-04-03 11:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0024_merge_20220403_1549'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicaluser',
            name='show_margin',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='show_margin',
            field=models.BooleanField(default=False),
        ),
    ]