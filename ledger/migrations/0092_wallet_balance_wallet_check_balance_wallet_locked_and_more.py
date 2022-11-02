# Generated by Django 4.0 on 2022-06-07 11:53

from decimal import Decimal
import django.core.validators
from django.db import migrations, models
import django.db.models.expressions
from django.db.models import Sum


def populate_wallet_balances(apps, schema_editor):
    Wallet = apps.get_model('ledger', 'Wallet')
    Trx = apps.get_model('ledger', 'Trx')
    BalanceLock = apps.get_model('ledger', 'BalanceLock')

    received = Trx.objects.values('receiver', 'receiver__market').annotate(amount=Sum('amount'))
    sent = Trx.objects.values('sender', 'sender__market').annotate(amount=Sum('amount'))

    received_dict = {}
    sent_dict = {}

    for r in received:
        received_dict[(r['receiver'], r['receiver__market'])] = r['amount']

    for s in sent:
        sent_dict[(s['sender'], s['sender__market'])] = s['amount']

    locked = BalanceLock.objects.filter(freed=False).values('wallet', 'wallet__market').annotate(amount=Sum('amount'))
    locked_dict = {}

    for l in locked:
        locked_dict[(l['wallet'], l['wallet__market'])] = l['amount']

    for w in Wallet.objects.all().prefetch_related('account'):
        key = (w.id, w.market)
        w.balance = received_dict.get(key, 0) - sent_dict.get(key, 0)
        w.locked = locked_dict.get(key, 0)
        w.check_balance = w.account.type is None
        w.save()


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0091_merge_0089_alter_trx_scope_0090_margintransfer_asset'),
    ]

    operations = [
        migrations.AddField(
            model_name='wallet',
            name='balance',
            field=models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddField(
            model_name='wallet',
            name='check_balance',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='wallet',
            name='locked',
            field=models.DecimalField(decimal_places=8, default=Decimal('0'), max_digits=30, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AddConstraint(
            model_name='wallet',
            constraint=models.CheckConstraint(check=models.Q(('check_balance', False), models.Q(models.Q(('market', 'loan'), _negated=True), ('balance__gte', 0), ('balance__gte', django.db.models.expressions.F('locked'))), models.Q(('market', 'loan'), ('balance__lte', 0), ('locked', 0)), _connector='OR'), name='valid_balance_constraint'),
        ),
        migrations.AddConstraint(
            model_name='wallet',
            constraint=models.CheckConstraint(check=models.Q(('locked__gte', 0)), name='valid_locked_constraint'),
        ),
        migrations.RunPython(
            code=populate_wallet_balances, reverse_code=migrations.RunPython.noop
        )
    ]