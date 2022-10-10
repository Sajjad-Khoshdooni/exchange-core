# Generated by Django 4.0 on 2022-10-04 12:29

from django.db import migrations, models
import django.db.models.deletion


def populate_achievement(apps, schema_editor):
    Achievement = apps.get_model('gamify', 'Achievement')
    Prize = apps.get_model('ledger', 'Prize')

    achievements = dict(Achievement.objects.values_list('scope', 'id'))

    prizes = Prize.objects.all()

    for p in prizes:
        p.achievement_id = achievements[p.scope]

    Prize.objects.bulk_update(prizes, ['achievement_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0088_alter_verificationcode_scope_auth2fa'),
        ('gamify', '0004_upgrade_achievements'),
        ('ledger', '0138_transfer_irt_value_transfer_usdt_value'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='prize',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='prize',
            name='achievement',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='gamify.achievement'),
            preserve_default=False,
        ),
        migrations.RunPython(populate_achievement, reverse_code=migrations.RunPython.noop),
        migrations.AddField(
            model_name='wallet',
            name='expiration',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='wallet',
            name='market',
            field=models.CharField(choices=[('spot', 'spot'), ('margin', 'margin'), ('loan', 'loan'), ('stake', 'stake'), ('voucher', 'voucher')], max_length=8),
        ),
        migrations.AlterUniqueTogether(
            name='prize',
            unique_together={('account', 'achievement', 'variant')},
        ),
        migrations.RemoveField(
            model_name='prize',
            name='scope',
        ),
        migrations.AlterField(
            model_name='prize',
            name='achievement',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gamify.achievement'),
        ),
    ]
