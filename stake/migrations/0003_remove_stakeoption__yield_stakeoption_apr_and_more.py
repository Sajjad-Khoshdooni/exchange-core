# Generated by Django 4.0 on 2022-07-12 14:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stake', '0002_alter_stakerequest_status'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='stakeoption',
            name='_yield',
        ),
        migrations.AddField(
            model_name='stakeoption',
            name='apr',
            field=models.DecimalField(blank=True, decimal_places=3, default=1, max_digits=6),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='stakerequest',
            name='status',
            field=models.CharField(choices=[('process', 'process'), ('pending', 'pending'), (' done', ' done'), ('cancel_process', 'cancel_process'), ('cancel_pending', 'cancel_pending'), ('cancel_complete', 'cancel_complete')], default='process', max_length=16),
        ),
    ]
