# Generated by Django 4.0 on 2022-06-27 10:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0062_remove_historicaluser_on_boarding_flow_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='externalnotification',
            options={'verbose_name': 'نوتیف\u200cهای بیرون پنل', 'verbose_name_plural': 'نوتیف\u200cهای بیرون پنل'},
        ),
        migrations.AlterField(
            model_name='externalnotification',
            name='scope',
            field=models.CharField(choices=[('level_2_prize', 'level_2_prize'), ('first_deposit_prize', 'first_deposit_prize'), ('trade_prize', 'trade_prize')], max_length=22, verbose_name='نوع'),
        ),
    ]
