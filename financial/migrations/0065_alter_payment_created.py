# Generated by Django 4.1.3 on 2022-12-12 10:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0064_alter_fiatwithdrawrequest_withdraw_channel'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='created',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
    ]