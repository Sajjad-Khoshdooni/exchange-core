# Generated by Django 4.0 on 2022-08-14 07:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0077_alter_historicaluser_national_code_phone_verified_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='finotechrequest',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.user'),
        ),
    ]
