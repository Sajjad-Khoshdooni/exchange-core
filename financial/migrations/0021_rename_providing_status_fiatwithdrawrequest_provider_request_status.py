# Generated by Django 4.0 on 2022-03-28 11:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0020_fiatwithdrawrequest_providing_status'),
    ]

    operations = [
        migrations.RenameField(
            model_name='fiatwithdrawrequest',
            old_name='providing_status',
            new_name='provider_request_status',
        ),
    ]
