# Generated by Django 4.1.3 on 2023-04-23 18:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0107_remove_appstatus_light_apk_remove_appstatus_pro_apk_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicaluser',
            name='show_staking',
            field=models.BooleanField(default=True, verbose_name='امکان مشاهده سرمایه\u200cگذاری'),
        ),
        migrations.AlterField(
            model_name='user',
            name='show_staking',
            field=models.BooleanField(default=True, verbose_name='امکان مشاهده سرمایه\u200cگذاری'),
        ),
    ]
