# Generated by Django 4.1.3 on 2023-07-15 11:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0096_alter_payment_group_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='description',
            field=models.CharField(blank=True, max_length=256),
        ),
    ]
