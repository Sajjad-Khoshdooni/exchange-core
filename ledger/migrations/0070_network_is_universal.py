# Generated by Django 4.0 on 2022-04-12 11:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0069_alter_addressbook_options_alter_addressbook_account_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='network',
            name='is_universal',
            field=models.BooleanField(default=False),
        ),
    ]