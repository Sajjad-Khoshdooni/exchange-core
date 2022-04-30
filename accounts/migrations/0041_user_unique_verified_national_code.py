# Generated by Django 4.0 on 2022-04-30 08:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0040_historicaluser_selfie_image_verifier_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(condition=models.Q(('level__gt', 1)), fields=('national_code',), name='unique_verified_national_code'),
        ),
    ]