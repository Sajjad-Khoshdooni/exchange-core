# Generated by Django 4.0 on 2022-02-15 13:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('provider', '0004_alter_providerorder_scope_providertransfer_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='providerorder',
            name='order_id',
            field=models.CharField(blank=True, max_length=64),
        ),
    ]