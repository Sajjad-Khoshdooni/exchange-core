# Generated by Django 4.0 on 2022-07-06 12:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0037_remove_fiatwithdrawrequest_lock'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gateway',
            name='type',
            field=models.CharField(choices=[('zarinpal', 'zarinpal'), ('payir', 'payir'), ('zibal', 'zibal')], max_length=8),
        ),
    ]
