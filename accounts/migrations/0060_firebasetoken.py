# Generated by Django 4.0 on 2022-06-15 12:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0059_remove_account_last_margin_warn_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='FirebaseToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=256, unique=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.user', unique=True)),
            ],
        ),
    ]
