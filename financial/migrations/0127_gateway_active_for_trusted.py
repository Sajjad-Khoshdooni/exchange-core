# Generated by Django 4.1.3 on 2024-02-15 12:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0126_alter_payment_group_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='gateway',
            name='active_for_trusted',
            field=models.BooleanField(default=False),
        ),
    ]