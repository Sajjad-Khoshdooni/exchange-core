# Generated by Django 4.0 on 2022-09-06 13:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stake', '0005_alter_stakerequest_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='stakeoption',
            name='precision',
            field=models.IntegerField(default=0),
        ),
    ]