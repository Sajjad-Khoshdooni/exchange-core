# Generated by Django 4.0 on 2022-07-10 13:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stake', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stakerequest',
            name='status',
            field=models.CharField(choices=[('process', 'process'), ('pending', 'pending'), (' done', ' done'), ('cancel_process', 'cancel_process'), ('cancel_pending', 'cancel_pending'), ('cancel_cancel', 'cancel_cancel')], default='process', max_length=16),
        ),
    ]
