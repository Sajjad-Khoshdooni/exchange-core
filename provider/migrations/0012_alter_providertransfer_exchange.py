# Generated by Django 4.0 on 2022-06-25 14:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('provider', '0011_alter_providerorder_exchange'),
    ]

    operations = [
        migrations.AlterField(
            model_name='providertransfer',
            name='exchange',
            field=models.CharField(default='interface', max_length=16),
        ),
    ]
