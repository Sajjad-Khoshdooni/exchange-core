# Generated by Django 4.1.3 on 2023-05-23 08:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0119_firebasetoken_native_app'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'permissions': [('can_generate_notification', 'Can Generate All Kind Of Notification')], 'verbose_name': 'user', 'verbose_name_plural': 'users'},
        ),
        migrations.AddField(
            model_name='smsnotification',
            name='content',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AlterField(
            model_name='smsnotification',
            name='template',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
    ]