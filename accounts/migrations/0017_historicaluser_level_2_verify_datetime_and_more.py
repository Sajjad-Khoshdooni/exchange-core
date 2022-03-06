# Generated by Django 4.0 on 2022-03-06 15:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0016_usercomment_historicalusercomment_historicaluser'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicaluser',
            name='level_2_verify_datetime',
            field=models.DateTimeField(blank=True, null=True, verbose_name='تاریخ تاپید سطح ۲'),
        ),
        migrations.AddField(
            model_name='historicaluser',
            name='level_3_verify_datetime',
            field=models.DateTimeField(blank=True, null=True, verbose_name='تاریخ تاپید سطح 3'),
        ),
        migrations.AddField(
            model_name='user',
            name='level_2_verify_datetime',
            field=models.DateTimeField(blank=True, null=True, verbose_name='تاریخ تاپید سطح ۲'),
        ),
        migrations.AddField(
            model_name='user',
            name='level_3_verify_datetime',
            field=models.DateTimeField(blank=True, null=True, verbose_name='تاریخ تاپید سطح 3'),
        ),
    ]
