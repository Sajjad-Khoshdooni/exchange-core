# Generated by Django 4.1.3 on 2023-06-10 14:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0123_alter_bulknotification_message'),
    ]

    operations = [
        migrations.AlterField(
            model_name='smsnotification',
            name='content',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
    ]
