# Generated by Django 4.0 on 2022-09-18 09:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0060_alter_marketingcost_unique_together'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fiatwithdrawrequest',
            name='withdraw_channel',
            field=models.CharField(choices=[('zibal', 'zibal'), ('payir', 'payir'), ('jibit', 'jibit')], default='payir', max_length=10),
        ),
        migrations.AlterField(
            model_name='gateway',
            name='type',
            field=models.CharField(choices=[('zarinpal', 'zarinpal'), ('payir', 'payir'), ('zibal', 'zibal'), ('jibit', 'jibit')], max_length=8),
        ),
    ]