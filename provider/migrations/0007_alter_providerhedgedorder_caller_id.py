# Generated by Django 4.0 on 2022-02-22 11:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('provider', '0006_alter_providerorder_market'),
    ]

    operations = [
        migrations.AlterField(
            model_name='providerhedgedorder',
            name='caller_id',
            field=models.CharField(blank=True, max_length=32, null=True, unique=True),
        ),
    ]
