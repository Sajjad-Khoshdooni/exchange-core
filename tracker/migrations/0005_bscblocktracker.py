# Generated by Django 4.0 on 2022-02-06 12:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0004_ethblocktracker_trxblocktracker_blocktracker_network_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='BSCBlockTracker',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('tracker.blocktracker',),
        ),
    ]