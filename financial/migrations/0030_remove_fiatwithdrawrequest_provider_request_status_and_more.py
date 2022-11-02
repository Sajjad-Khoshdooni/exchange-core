# Generated by Django 4.0 on 2022-05-08 14:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0029_merge_20220508_1747'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='fiatwithdrawrequest',
            name='provider_request_status',
        ),
        migrations.AddField(
            model_name='fiatwithdrawrequest',
            name='provider_withdraw_id',
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AlterField(
            model_name='fiatwithdrawrequest',
            name='status',
            field=models.CharField(choices=[('process', 'در حال پردازش'), ('pending', 'در انتظار'), ('done', 'انجام شده'), ('canceled', 'لغو شده')], default='process', max_length=10),
        ),
    ]