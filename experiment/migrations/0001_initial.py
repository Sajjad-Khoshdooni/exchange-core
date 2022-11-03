# Generated by Django 4.0 on 2022-11-03 12:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0089_historicaluser_promotion_user_promotion'),
    ]

    operations = [
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('token', models.CharField(db_index=True, max_length=6, unique=True)),
                ('destination', models.URLField()),
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
                ('type', models.CharField(choices=[('sms_notif', 'sms_notif')], max_length=30)),
                ('data', models.JSONField()),
            ],
        ),
        migrations.CreateModel(
            name='VariantUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('is_done', models.BooleanField(db_index=True, default=False)),
                ('link', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='experiment.link')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.user')),
                ('variant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='experiment.variant')),
            ],
        ),
        migrations.CreateModel(
            name='Experiment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=20)),
                ('active', models.BooleanField(db_index=True, default=True)),
                ('a_variant', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='VARIANT_A', to='experiment.variant')),
                ('b_variant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='VARIANT_B', to='experiment.variant')),
            ],
        ),
        migrations.CreateModel(
            name='Click',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('user_agent', models.CharField(max_length=500)),
                ('link', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='experiment.link')),
            ],
        ),
    ]
