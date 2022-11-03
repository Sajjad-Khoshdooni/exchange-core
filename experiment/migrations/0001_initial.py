# Generated by Django 4.0 on 2022-11-03 14:28

from django.db import migrations, models
import django.db.models.deletion
import experiment.models.link


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0089_historicaluser_promotion_user_promotion'),
    ]

    operations = [
        migrations.CreateModel(
            name='Experiment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=20)),
                ('active', models.BooleanField(db_index=True, default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('token', models.CharField(db_index=True, default=experiment.models.link.create_token, max_length=6, unique=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.user')),
            ],
        ),
        migrations.CreateModel(
            name='Variant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=20)),
                ('type', models.CharField(blank=True, choices=[('sms_notif', 'sms_notif')], max_length=30)),
                ('data', models.JSONField(blank=True, null=True)),
                ('experiment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='experiment.experiment')),
            ],
        ),
        migrations.CreateModel(
            name='Click',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('user_agent', models.TextField(blank=True)),
                ('link', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='experiment.link')),
            ],
        ),
        migrations.CreateModel(
            name='VariantUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('triggered', models.BooleanField(db_index=True, default=False)),
                ('link', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='experiment.link')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.user')),
                ('variant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='experiment.variant')),
            ],
            options={
                'unique_together': {('user', 'variant')},
            },
        ),
    ]
