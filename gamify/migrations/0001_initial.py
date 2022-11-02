# Generated by Django 4.0 on 2022-10-02 11:51

import django.db.models.deletion
from django.db import migrations, models
from decouple import config

from accounts.models import Notification


def populate_missions(apps, schema_editor):
    Mission = apps.get_model('gamify', 'Mission')
    MissionJourney = apps.get_model('gamify', 'MissionJourney')
    Task = apps.get_model('gamify', 'Task')
    Achievement = apps.get_model('gamify', 'Achievement')

    journey = MissionJourney.objects.create(name='default', active=True)

    mission = Mission.objects.create(journey=journey, name='verify', order=0)
    Task.objects.create(
        mission=mission,
        scope='verify_level2',
        type='bool',
        title='احراز هویت',
        link='/account/verification/basic',
        description='احراز هویت کنید و شیبا جایزه بگیرید.'.format(config('BRAND')),
        level=Notification.ERROR,
    )
    Achievement.objects.create(
        mission=mission,
        scope='level2_verify'
    )

    mission = Mission.objects.create(journey=journey, name='trade', order=1)
    Task.objects.create(
        mission=mission,
        scope='deposit',
        type='bool',
        title='واریز',
        link='/wallet/spot/money-deposit',
        description='با واریز وجه، تنها چند ثانیه با خرید و فروش رمزارز فاصله دارید.',
        level=Notification.WARNING,
    )
    Task.objects.create(
        mission=mission,
        scope='trade',
        max=2_000_000,
        title='معامله',
        link='/trade/classic/BTCIRT',
        description='به ارزش ۲ میلیون تومان معامله کنید.',
        level=Notification.WARNING,
    )
    Achievement.objects.create(
        mission=mission,
        scope='trade_2m'
    )

    mission = Mission.objects.create(journey=journey, name='trade2', order=2)
    Task.objects.create(
        mission=mission,
        scope='trade',
        max=20_000_000,
        title='معامله',
        link='/trade/classic/BTCIRT',
        description='به ارزش ۲۰ میلیون تومان معامله کنید.',
        level=Notification.WARNING,
    )
    Achievement.objects.create(
        mission=mission,
        scope='trade_s2'
    )


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='MissionJourney',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64)),
                ('active', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Mission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64)),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('journey', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gamify.missionjourney')),
            ],
            options={
                'ordering': ('order',),
            },
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('scope', models.CharField(choices=[('verify_level2', 'verify_level2'), ('deposit', 'deposit'), ('trade', 'trade'), ('referral', 'referral'), ('set_email', 'set_email')], max_length=16)),
                ('type', models.CharField(choices=[('bool', 'bool'), ('number', 'number')], default='number', max_length=8)),
                ('max', models.PositiveIntegerField(default=1)),
                ('title', models.CharField(max_length=32)),
                ('link', models.CharField(max_length=32)),
                ('description', models.CharField(max_length=128)),
                ('level', models.CharField(choices=[('info', 'info'), ('success', 'success'), ('warning', 'warning'), ('error', 'error')], default='warning', max_length=8)),
                ('mission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gamify.mission')),
            ],
            options={
                'ordering': ('order',),
            },
        ),
        migrations.CreateModel(
            name='Achievement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scope', models.CharField(choices=[('level2_verify', 'level2_verify'), ('trade_2m', 'trade_2m'), ('trade_s2', 'trade_s2'), ('referral_trade_2m', 'referral_trade_2m')], max_length=32)),
                ('mission', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='gamify.mission')),
            ],
        ),
        migrations.RunPython(code=populate_missions, reverse_code=migrations.RunPython.noop)
    ]