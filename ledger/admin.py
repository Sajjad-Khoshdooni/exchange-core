from datetime import timedelta
from uuid import uuid4

from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import F, Sum, Q
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter
from simple_history.admin import SimpleHistoryAdmin

from accounting.models import ReservedAsset
from accounts.admin_guard import M
from accounts.admin_guard.admin import AdvancedAdmin
from accounts.admin_guard.html_tags import anchor_tag
from accounts.models import Account, User
from accounts.utils.admin import url_to_edit_object
from accounts.utils.validation import gregorian_to_jalali_datetime_str
from financial.models import Payment
from ledger import models
from ledger.models import Asset, Prize, CoinCategory, FastBuyToken, Network, ManualTransaction, BalanceLock, Wallet
from ledger.utils.external_price import get_external_price, BUY
from ledger.utils.fields import DONE, PROCESS
from ledger.utils.precision import get_presentation_amount, humanize_presentation
from ledger.utils.precision import humanize_number
from ledger.utils.provider import get_provider_requester
from ledger.utils.withdraw_verify import RiskFactor
from market.utils.fix import create_symbols_for_asset


@admin.register(models.Asset)
class AssetAdmin(AdvancedAdmin):
    default_edit_condition = M.superuser

    fields_edit_conditions = {
        'order': True,
        'trend': True,
    }

    list_display = (
        'symbol', 'enable', 'get_hedge_value', 'get_hedge_value_abs', 'get_hedge_amount', 'get_calc_hedge_amount',
        'get_total_asset', 'get_users_balance', 'get_reserved_amount',
        'order', 'trend', 'trade_enable', 'hedge',
        'margin_enable', 'publish_date', 'spread_category', 'otc_status'
    )
    list_filter = ('enable', 'trend', 'margin_enable', 'spread_category')
    list_editable = ('enable', 'order', 'trend', 'trade_enable', 'margin_enable', 'hedge')
    search_fields = ('symbol', )
    ordering = ('-enable', '-pin_to_top', '-trend', 'order')
    actions = ('setup_asset', )

    def save_model(self, request, obj, form, change):
        if Asset.objects.filter(order=obj.order).exclude(id=obj.id).exists():
            Asset.objects.filter(order__gte=obj.order).exclude(id=obj.id).update(order=F('order') + 1)

        return super(AssetAdmin, self).save_model(request, obj, form, change)

    def get_queryset(self, request):
        return super(AssetAdmin, self).get_queryset(request)\
            .annotate(
                hedge_value=F('assetsnapshot__hedge_value'),
                hedge_value_abs=F('assetsnapshot__hedge_value_abs'),
                hedge_amount=F('assetsnapshot__hedge_amount'),
                calc_hedge_amount=F('assetsnapshot__calc_hedge_amount'),
                users_amount=F('assetsnapshot__users_amount'),
                total_amount=F('assetsnapshot__total_amount'),
            )

    @admin.display(description='users')
    def get_users_balance(self, asset: Asset):
        users_amount = asset.users_amount

        if users_amount is None:
            return

        return humanize_presentation(users_amount)

    @admin.display(description='total assets')
    def get_total_asset(self, asset: Asset):
        total_amount = asset.total_amount

        if total_amount is None:
            return

        return humanize_presentation(total_amount)

    @admin.display(description='hedge amount')
    def get_hedge_amount(self, asset: Asset):
        hedge_amount = asset.hedge_amount

        if hedge_amount is None:
            return

        return humanize_presentation(hedge_amount)

    @admin.display(description='calc hedge amount')
    def get_calc_hedge_amount(self, asset: Asset):
        calc_hedge_amount = asset.calc_hedge_amount

        if calc_hedge_amount is None:
            return

        return humanize_presentation(calc_hedge_amount)

    @admin.display(description='reserved amount')
    def get_reserved_amount(self, asset: Asset):
        return ReservedAsset.objects.filter(coin=asset.symbol).aggregate(s=Sum('amount'))['s']

    @admin.display(description='hedge value', ordering='hedge_value')
    def get_hedge_value(self, asset: Asset):
        hedge_value = asset.hedge_value

        if hedge_value is None:
            return

        hedge_value = round(hedge_value, 2)

        return humanize_presentation(hedge_value)

    @admin.display(description='hedge value abs', ordering='hedge_value_abs')
    def get_hedge_value_abs(self, asset: Asset):
        hedge_value_abs = asset.hedge_value_abs

        if hedge_value_abs is None:
            return

        hedge_value_abs = round(hedge_value_abs, 2)

        return humanize_presentation(hedge_value_abs)

    @admin.action(description='setup asset', permissions=['view'])
    def setup_asset(self, request, queryset):
        from ledger.models import NetworkAsset

        for asset in queryset:
            networks_info = get_provider_requester().get_network_info(asset.symbol)

            for info in networks_info:
                network, _ = Network.objects.get_or_create(
                    symbol=info.network,
                    defaults={
                        'can_deposit': False,
                        'can_withdraw': False,
                        'address_regex': info.address_regex
                    }
                )

                ns, _ = NetworkAsset.objects.get_or_create(
                    asset=asset,
                    network=network,

                    defaults={
                        'withdraw_fee': info.withdraw_fee,
                        'withdraw_min': info.withdraw_min,
                        'withdraw_max': info.withdraw_max,
                        'withdraw_precision': 0,
                    }
                )

                ns.update_with_provider(info)

            create_symbols_for_asset(asset)


@admin.register(models.Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'can_withdraw', 'can_deposit', 'min_confirm', 'unlock_confirm', 'need_memo', 'address_regex')
    list_editable = ('can_withdraw', 'can_deposit')
    search_fields = ('symbol', )
    list_filter = ('can_withdraw', 'can_deposit')
    ordering = ('-can_withdraw', '-can_deposit')


@admin.register(models.NetworkAsset)
class NetworkAssetAdmin(admin.ModelAdmin):
    list_display = ('network', 'asset', 'withdraw_fee', 'withdraw_min', 'withdraw_max', 'can_deposit', 'can_withdraw',
                    'allow_provider_withdraw', 'hedger_withdraw_enable', 'update_fee_with_provider')
    search_fields = ('asset__symbol', )
    list_editable = ('can_deposit', 'can_withdraw', 'allow_provider_withdraw', 'hedger_withdraw_enable',
                     'update_fee_with_provider')
    list_filter = ('network', 'allow_provider_withdraw', 'hedger_withdraw_enable', 'update_fee_with_provider')


class DepositAddressUserFilter(admin.SimpleListFilter):
    title = 'کاربران'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        user = request.GET.get('user')
        if user is not None:
            return queryset.filter(address_key__account__user=user)
        else:
            return queryset


@admin.register(models.DepositAddress)
class DepositAddressAdmin(admin.ModelAdmin):
    list_display = ('address_key', 'network', 'address',)
    readonly_fields = ('address_key', 'network', 'address',)
    list_filter = ('network', DepositAddressUserFilter)
    search_fields = ('address',)


class OTCRequestUserFilter(SimpleListFilter):
    title = 'کاربر'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        user = request.GET.get('user')
        if user is not None:
            return queryset.filter(account__user_id=user)
        else:
            return queryset


@admin.register(models.OTCRequest)
class OTCRequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'symbol', 'side', 'price', 'amount', 'fee_amount', 'fee_revenue')
    readonly_fields = ('account', 'login_activity')
    search_fields = ('token', )
    list_filter = (OTCRequestUserFilter, )


class OTCUserFilter(SimpleListFilter):
    title = 'کاربر'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        user = request.GET.get('user')
        if user is not None:
            return queryset.filter(otc_request__account__user_id=user)
        else:
            return queryset


@admin.register(models.OTCTrade)
class OTCTradeAdmin(admin.ModelAdmin):
    list_display = ('created', 'otc_request', 'status', 'get_value', 'get_value_irt', 'execution_type', 'gap_revenue')
    list_filter = (OTCUserFilter, 'status')
    search_fields = ('group_id', 'order_id', 'otc_request__symbol__asset__symbol', 'otc_request__account__user__phone')
    readonly_fields = ('otc_request', )
    actions = ('accept_trade', 'accept_trade_without_hedge', 'cancel_trade')

    @admin.display(description='value')
    def get_value(self, otc_trade: models.OTCTrade):
        return humanize_number(round(otc_trade.otc_request.usdt_value, 2))

    @admin.display(description='value_irt')
    def get_value_irt(self, otc_trade: models.OTCTrade):
        return humanize_number(round(otc_trade.otc_request.irt_value, 0))

    @admin.action(description='Accept Trade')
    def accept_trade(self, request, queryset):
        for otc in queryset.filter(status='pending'):
            otc.hedge_with_provider()

    @admin.action(description='Accept without Hedge')
    def accept_trade_without_hedge(self, request, queryset):
        for otc in queryset.filter(status='pending'):
            otc.hedge_with_provider(hedge=False)

    @admin.action(description='Cancel Trade')
    def cancel_trade(self, request, queryset):
        for otc in queryset.filter(status='pending'):
            otc.cancel()


@admin.register(models.Trx)
class TrxAdmin(admin.ModelAdmin):
    list_display = ('created', 'sender', 'receiver', 'amount', 'scope', 'group_id')
    search_fields = ('sender__asset__symbol', 'sender__account__user__phone', 'receiver__account__user__phone', 'group_id')
    readonly_fields = ('sender', 'receiver', )
    list_filter = ('scope', )


class WalletUserFilter(SimpleListFilter):
    title = 'کاربر'
    parameter_name = 'account'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        account = request.GET.get('account')
        if account is not None:
            return queryset.filter(account=account)
        else:
            return queryset


@admin.register(models.Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'asset', 'market', 'get_free', 'locked', 'get_value_usdt', 'get_value_irt',
                    'credit')
    list_filter = [
        ('asset', RelatedDropdownFilter),
        WalletUserFilter
    ]
    readonly_fields = ('account', 'asset', 'market', 'balance', 'locked')
    search_fields = ('account__user__phone', 'asset__symbol')

    @admin.display(description='free')
    def get_free(self, wallet: models.Wallet):
        return wallet.get_free()

    @admin.display(description='irt value')
    def get_value_irt(self, wallet: models.Wallet):
        price = get_external_price(
            coin=wallet.asset.symbol,
            base_coin=Asset.IRT,
            side=BUY
        ) or 0
        return wallet.asset.get_presentation_price_irt(wallet.balance * price)

    @admin.display(description='usdt value')
    def get_value_usdt(self, wallet: models.Wallet):
        price = get_external_price(
            coin=wallet.asset.symbol,
            base_coin=Asset.USDT,
            side=BUY
        ) or 0
        return wallet.asset.get_presentation_price_usdt(wallet.balance * price)


class TransferUserFilter(SimpleListFilter):
    title = 'کاربر'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        user = request.GET.get('user')
        if user is not None:
            return queryset.filter(wallet__account__user_id=user)
        else:
            return queryset


@admin.register(models.Transfer)
class TransferAdmin(AdvancedAdmin):
    default_edit_condition = M.superuser

    fields_edit_conditions = {
        'comment': True,
        'status': True,
        'trx_hash': True,
    }

    list_display = (
        'created', 'network', 'get_asset', 'amount', 'fee_amount', 'deposit', 'status', 'source', 'get_user',
        'usdt_value', 'get_remaining_time_to_pass_48h', 'get_jalali_created', 'get_jalali_finished'
    )
    search_fields = ('trx_hash', 'out_address', 'wallet__asset__symbol')
    list_filter = ('deposit', 'status', 'source', TransferUserFilter,)
    readonly_fields = (
        'deposit_address', 'network', 'wallet', 'created', 'accepted_datetime', 'finished_datetime', 'get_risks',
        'out_address', 'memo', 'amount', 'irt_value', 'usdt_value', 'deposit', 'group_id', 'login_activity'
    )
    exclude = ('risks', )

    actions = ('accept_withdraw', 'reject_withdraw')

    def save_model(self, request, obj: models.Transfer, form, change):
        if obj.id and obj.status == models.Transfer.DONE:
            old = models.Transfer.objects.get(id=obj.id)

            if old.status != models.Transfer.DONE:
                old.accept(obj.trx_hash)

        obj.save()

    def get_queryset(self, request):
        return super(TransferAdmin, self).get_queryset(request).select_related('wallet__account__user')

    @admin.display(description='Asset')
    def get_asset(self, transfer: models.Transfer):
        return transfer.wallet.asset

    @admin.display(description='created jalali')
    def get_jalali_created(self, transfer: models.Transfer):
        return gregorian_to_jalali_datetime_str(transfer.created)

    @admin.display(description='finished jalali')
    def get_jalali_finished(self, transfer: models.Transfer):
        return transfer.finished_datetime and gregorian_to_jalali_datetime_str(transfer.finished_datetime)

    @admin.display(description='User')
    def get_user(self, transfer: models.Transfer):
        user = transfer.wallet.account.user

        if user:
            link = url_to_edit_object(user)
            return anchor_tag(user.phone, link)

    @admin.display(description='Remaining 48h')
    def get_remaining_time_to_pass_48h(self, transfer: models.Transfer):
        if transfer.deposit:
            return

        user = transfer.wallet.account.user

        last_payment = Payment.objects.filter(
            Q(payment_request__bank_card__user=user) | Q(payment_id_request__payment_id__user=user),
            created__gt=timezone.now() - timedelta(days=3),
            created__lt=transfer.created,
            status=DONE,
        ).order_by('created').last()

        if last_payment:
            passed = timezone.now() - last_payment.created
            rem = timedelta(days=2) - passed
            return '%s روز %s ساعت %s دقیقه' % (rem.days, rem.seconds // 3600, rem.seconds % 3600 // 60)

    @admin.display(description='risks')
    def get_risks(self, transfer):
        if not transfer.risks:
            return
        html = '<table dir="ltr"><tr><th>Factor</th><th>Value</th><th>Expected</th><th>Whitelist</th></tr>'

        for risk in transfer.risks:
            html += '<tr><td>{reason}</td><td>{value}</td><td>{expected}</td><td>{whitelist}</td></tr>'.format(
                **RiskFactor(**risk).__dict__
            )

        html += '</table>'

        return mark_safe(html)

    @admin.action(description='تایید برداشت', permissions=['view'])
    def accept_withdraw(self, request, queryset):
        queryset.filter(status=models.Transfer.INIT).update(
            status=models.Transfer.PROCESSING,
            accepted_datetime=timezone.now(),
        )

    @admin.action(description='رد برداشت', permissions=['view'])
    def reject_withdraw(self, request, queryset):
        for transfer in queryset.filter(status=models.Transfer.INIT):
            transfer.reject()


class CryptoAccountTypeFilter(SimpleListFilter):
    title = 'type'
    parameter_name = 'type'

    def lookups(self, request, model_admin):
        return (Account.SYSTEM, 'system'), (Account.OUT, 'out'), ('ord', 'ordinary')

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            if value == 'ord':
                value = None

            return queryset.filter(deposit_address__address_key__account__type=value)
        else:
            return queryset


@admin.register(models.MarginTransfer)
class MarginTransferAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'amount', 'type', )
    search_fields = ('group_id',)


@admin.register(models.MarginLoan)
class MarginLoanAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'amount', 'type', 'asset', 'status')
    search_fields = ('group_id',)


@admin.register(models.CloseRequest)
class CloseRequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'margin_level', 'group_id', 'status')
    search_fields = ('group_id',)
    list_filter = ('status', )
    readonly_fields = ('account', 'created', 'group_id')


@admin.register(models.AddressBook)
class AddressBookAdmin(admin.ModelAdmin):
    list_display = ('name', 'account', 'network', 'address', 'asset',)
    search_fields = ('address', 'name')


class PrizeUserFilter(admin.SimpleListFilter):
    title = 'کاربران'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        user = request.GET.get('user')
        if user is not None:
            return queryset.filter(account__user_id=user)
        else:
            return queryset


@admin.register(models.Prize)
class PrizeAdmin(admin.ModelAdmin):
    list_display = ('created', 'achievement', 'account', 'get_asset_amount', 'redeemed', 'value')
    readonly_fields = ('account', 'asset', )
    list_filter = ('achievement', 'redeemed', PrizeUserFilter)

    def get_asset_amount(self, prize: Prize):
        return '%s %s' % (get_presentation_amount(prize.amount), prize.asset)

    get_asset_amount.short_description = 'مقدار'


@admin.register(models.CoinCategory)
class CoinCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_coin_count']

    def get_coin_count(self, coin_category: CoinCategory):
        return coin_category.coins.filter(enable=True).count()

    get_coin_count.short_description = 'تعداد رمزارز'


@admin.register(models.AddressKey)
class AddressKeyAdmin(admin.ModelAdmin):
    list_display = ('address', 'deleted', 'account', 'architecture')
    readonly_fields = ('address', 'account')
    search_fields = ('address', 'public_address', 'account__user__phone')
    list_filter = ('architecture', 'deleted', 'architecture')


@admin.register(models.AssetSpreadCategory)
class AssetSpreadCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', )


@admin.register(models.MarketSpread)
class MarketSpreadAdmin(admin.ModelAdmin):
    list_display = ('id', 'step', 'side', 'spread')
    list_editable = ('side', 'step', 'spread')
    ordering = ('step', 'side')
    list_filter = ('side', 'step')


@admin.register(models.PNLHistory)
class PNLHistoryAdmin(admin.ModelAdmin):
    list_display = ('date', 'account', 'market', 'base_asset', 'snapshot_balance', 'profit')
    readonly_fields = ('date', 'account', 'market', 'base_asset', 'snapshot_balance', 'profit')


@admin.register(models.CategorySpread)
class CategorySpreadAdmin(admin.ModelAdmin):
    list_display = ('category', 'step', 'side', 'spread')
    list_editable = ('side', 'step', 'spread')
    ordering = ('category', 'step', 'side')
    list_filter = ('category', 'side', 'step')


@admin.register(models.SystemSnapshot)
class SystemSnapshotAdmin(admin.ModelAdmin):
    list_display = ('created', 'total', 'users', 'exchange', 'exchange_potential', 'hedge', 'prize')
    ordering = ('-created', )
    actions = ('reject_histories', 'verify_histories')
    readonly_fields = ('created', )

    @admin.action(description='رد', permissions=['change'])
    def reject_histories(self, request, queryset):
        queryset.update(verified=False)

    @admin.action(description='تایید', permissions=['change'])
    def verify_histories(self, request, queryset):
        queryset.update(verified=True)


@admin.register(models.AssetSnapshot)
class AssetSnapshotAdmin(SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ('updated', 'asset', 'total_amount', 'users_amount', 'hedge_amount', 'hedge_value', 'get_hedge_diff')
    ordering = ('asset__order', )
    list_filter = ('asset', )

    def get_hedge_diff(self, asset_snapshot: models.AssetSnapshot):
        return asset_snapshot.calc_hedge_amount - asset_snapshot.hedge_amount

    get_hedge_diff.short_description = 'hedge diff'


@admin.register(models.FastBuyToken)
class FastBuyTokenAdmin(admin.ModelAdmin):
    list_display = ['created', 'asset', 'get_amount', 'status', ]
    readonly_fields = ('get_amount', 'payment_request', 'otc_request')
    list_filter = ('status', )

    def get_amount(self, fast_buy_token: FastBuyToken):
        return humanize_number(fast_buy_token.amount)

    get_amount.short_description = 'مقدار'


class ManualTransactionForm(forms.ModelForm):
    user = forms.IntegerField(required=False)
    asset = forms.ModelChoiceField(required=False, queryset=Asset.objects.filter(enable=True))
    market = forms.ChoiceField(choices=Wallet.MARKET_CHOICES, initial=Wallet.SPOT)
    wallet = forms.IntegerField(required=False, disabled=True)

    def clean(self):
        wallet_id = self.cleaned_data['wallet']
        if not wallet_id:
            account = Account.objects.filter(user_id=self.cleaned_data['user']).first()
            if not account:
                self.add_error('user', _("Please specify valid user id"))
                return
            asset = self.cleaned_data['asset']
            if not asset:
                self.add_error('asset', _("Please specify asset"))
                return
            self.cleaned_data['wallet'] = asset.get_wallet(account, market=self.cleaned_data['market'])
        else:
            self.cleaned_data['wallet'] = Wallet.objects.get(id=wallet_id)

        return super(ManualTransactionForm, self).clean()

    class Meta:
        model = ManualTransaction
        fields = '__all__'


@admin.register(ManualTransaction)
class ManualTransactionAdmin(admin.ModelAdmin):
    form = ManualTransactionForm
    list_display = ('created', 'wallet', 'type', 'status', 'amount')
    list_filter = ('type', 'status')
    ordering = ('-created', )
    readonly_fields = ('group_id', )
    actions = ('clone_transaction', )

    @admin.action(description='Clone')
    def clone_transaction(self, request, queryset):
        for trx in queryset:
            trx.id = None
            trx.status = PROCESS
            trx.group_id = uuid4()
            trx.save()


@admin.register(BalanceLock)
class BalanceLockAdmin(admin.ModelAdmin):
    list_display = ('created', 'key', 'wallet', 'original_amount', 'amount', 'reason')
    readonly_fields = ('wallet', 'key', 'original_amount', 'amount', 'reason')
    list_filter = ('reason', )
    search_fields = ('wallet__account__user__phone', 'key')
