# Generated by Django 4.1.3 on 2023-12-26 10:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0173_systemconfig_insurance_fee_percentage_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='systemconfig',
            name='mean_leverage',
        ),
        migrations.AddField(
            model_name='systemconfig',
            name='default_margin_leverage',
            field=models.SmallIntegerField(default=3),
        ),
        migrations.AlterField(
            model_name='systemconfig',
            name='max_margin_leverage',
            field=models.SmallIntegerField(default=5),
        ),
    ]