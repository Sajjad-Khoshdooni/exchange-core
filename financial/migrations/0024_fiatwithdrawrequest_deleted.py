# Generated by Django 4.0 on 2022-04-26 06:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0023_fiatwithdrawrequest_comment'),
    ]

    operations = [
        migrations.AddField(
            model_name='fiatwithdrawrequest',
            name='deleted',
            field=models.BooleanField(default=False),
        ),
    ]
