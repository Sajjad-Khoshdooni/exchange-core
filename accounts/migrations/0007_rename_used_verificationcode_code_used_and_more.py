# Generated by Django 4.0 on 2021-12-29 09:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_rename_phone_number_verificationcode_phone_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='verificationcode',
            old_name='used',
            new_name='code_used',
        ),
        migrations.AddField(
            model_name='verificationcode',
            name='token_used',
            field=models.BooleanField(default=False),
        ),
    ]
