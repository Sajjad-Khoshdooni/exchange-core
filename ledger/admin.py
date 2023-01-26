from datetime import timedelta
from uuid import uuid4

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import F
from django.utils import timezone
from django.utils.safestring import mark_safe
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter

from accounts.admin_guard import M
from accounts.admin_guard.admin import AdvancedAdmin
from accounts.admin_guard.html_tags import anchor_tag
from accounts.models import Account
from accounts.utils.admin import url_to_edit_object
from accounts.utils.validation import gregorian_to_jalali_datetime_str
from financial.models import Payment
from ledger import models
from ledger.models import Asset, Prize, CoinCategory, FastBuyToken
from ledger.utils.fields import DONE
from ledger.utils.overview import AssetOverview
from ledger.utils.precision import get_presentation_amount, humanize_presentation
from ledger.utils.precision import humanize_number
from ledger.utils.price import get_trading_price_usdt, SELL
from ledger.utils.provider import HEDGE, get_provider_requester
from ledger.utils.withdraw_verify import RiskFactor


@admin.register(models.Asset)
class AssetAdmin(AdvancedAdmin):
    default_edit_condition = M.superuser

    fields_edit_conditions = {
        'order': True,
        'trend': True,
    }

    readonly_fields = ('get_calc_hedge_amount', 'get_hedge_value', 'get_hedge_amount')

    list_display = (
        'symbol', 'enable', 'get_hedge_value', 'get_hedge_amount', 'get_calc_hedge_amount',
        'get_total_asset', 'get_users_balance',
        'order', 'trend', 'trade_enable', 'hedge',
        'margin_enable', 'new_coin', 'spread_category'
    )
    list_filter = ('enable', 'trend', 'margin_enable', 'spread_category')
    list_editable = ('enable', 'order', 'trend', 'trade_enable', 'margin_enable', 'new_coin', 'hedge')
    search_fields = ('symbol', )
    ordering = ('-enable', '-pin_to_top', '-trend', 'order')
    actions = ('hedge_asset', )

    def changelist_view(self, request, extra_context=None):
        self.overview = AssetOverview(calculated_hedge=True)

        context = {
            'hedge_value': round(self.overview.get_total_hedge_value(), 2),
            'margin_insurance_balance': self.overview.get_margin_insurance_balance(),
            'binance_margin_ratio': round(self.overview.get_binance_margin_ratio(), 2),

            'total_assets_usdt': round(self.overview.get_all_real_assets_value(), 0),
            'exchange_assets_usdt': round(self.overview.get_exchange_assets_usdt(), 0),
            'exchange_potential_usdt': round(self.overview.get_exchange_potential_usdt(), 0),
            'users_usdt': round(self.overview.get_all_users_asset_value(), 0)
        }

        return super().changelist_view(request, extra_context=context)

    def save_model(self, request, obj, form, change):
        if Asset.objects.filter(order=obj.order).exclude(id=obj.id).exists():
            Asset.objects.filter(order__gte=obj.order).exclude(id=obj.id).update(order=F('order') + 1)

        return super(AssetAdmin, self).save_model(request, obj, form, change)

    @admin.display(description='users')
    def get_users_balance(self, asset: Asset):
        return humanize_presentation(self.overview.get_users_asset_amount(asset.symbol))
    
    @admin.display(description='total assets')
    def get_total_asset(self, asset: Asset):
        return humanize_presentation(self.overview.get_real_assets(asset.symbol))

    @admin.display(description='hedge amount')
    def get_hedge_amount(self, asset: Asset):
        return humanize_presentation(self.overview.get_hedge_amount(asset.symbol))

    @admin.display(description='calc hedge amount')
    def get_calc_hedge_amount(self, asset: Asset):
        return humanize_presentation(self.overview.get_calculated_hedge(asset.symbol))

    @admin.display(description='hedge value')
    def get_hedge_value(self, asset: Asset):
        hedge_value = self.overview.get_hedge_value(asset.symbol)

        if hedge_value is not None:
            hedge_value = round(hedge_value, 2)

        return humanize_presentation(hedge_value)

    @admin.action(description='hedge assets', permissions=['view'])
    def hedge_asset(self, request, queryset):
        assets = queryset.filter(hedge=True)
        for asset in assets:
            get_provider_requester().try_hedge_new_order(
                request_id='manual:%s' % uuid4(),
                asset=asset,
                scope=HEDGE
            )


@admin.register(models.Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'can_withdraw', 'can_deposit', 'min_confirm', 'unlock_confirm', 'address_regex')
    list_editable = ('can_withdraw', 'can_deposit')
    search_fields = ('symbol', )
    list_filter = ('can_withdraw', 'can_deposit')
    ordering = ('-can_withdraw', '-can_deposit')


@admin.register(models.NetworkAsset)
class NetworkAssetAdmin(admin.ModelAdmin):
    list_display = ('network', 'asset', 'withdraw_fee', 'withdraw_min', 'withdraw_max', 'can_deposit', 'can_withdraw',
                    'allow_provider_withdraw', 'hedger_withdraw_enable')
    search_fields = ('asset__symbol', )
    list_editable = ('can_deposit', 'can_withdraw', 'allow_provider_withdraw')
    list_filter = ('network', 'allow_provider_withdraw')


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


@admin.register(models.OTCRequest)
class OTCRequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'from_asset', 'to_asset', 'to_price', 'from_amount', 'to_amount', 'token')
    readonly_fields = ('account', )

    def get_from_amount(self, otc_request: models.OTCRequest):
        return humanize_number((otc_request.from_asset.get_presentation_amount(otc_request.from_amount)))

    get_from_amount.short_description = 'from_amount'

    def get_to_amount(self, otc_request: models.OTCRequest):
        return otc_request.to_asset.get_presentation_amount(otc_request.to_amount)

    get_to_amount.short_description = 'to_amount'

    def get_to_price(self, otc_request: models.OTCRequest):
        return otc_request.to_asset.get_presentation_amount(otc_request.to_price)

    get_to_price.short_description = 'to_price'


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
    list_display = ('created', 'otc_request', 'status', 'get_otc_trade_to_price_absolute_irt', )
    list_filter = (OTCUserFilter, 'status')
    search_fields = ('group_id', )
    readonly_fields = ('otc_request', )
    actions = ('accept_trade', 'accept_trade_without_hedge', 'cancel_trade')

    def get_otc_trade_from_amount(self, otc_trade: models.OTCTrade):
        return humanize_number(
            otc_trade.otc_request.from_asset.get_presentation_amount(otc_trade.otc_request.from_amount)
        )

    get_otc_trade_from_amount.short_description = 'مقدار پایه'

    def get_otc_trade_to_price_absolute_irt(self, otc_trade: models.OTCTrade):
        return humanize_number(int(
            otc_trade.otc_request.to_price_absolute_irt * otc_trade.otc_request.to_amount
        ))
    get_otc_trade_to_price_absolute_irt.short_description = 'ارزش ریالی'

    @admin.action(description='تایید معامله')
    def accept_trade(self, request, queryset):
        for otc in queryset.filter(status='pending'):
            otc.accept()

    @admin.action(description='تایید معامله بدون هج')
    def accept_trade_without_hedge(self, request, queryset):
        for otc in queryset.filter(status='pending'):
            otc.accept(hedge=False)

    @admin.action(description='لغو معامله')
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
    list_display = ('created', 'account', 'asset', 'market', 'get_free', 'get_locked', 'get_free_usdt', 'get_free_irt')
    list_filter = [
        ('asset', RelatedDropdownFilter),
        WalletUserFilter
    ]
    readonly_fields = ('account', 'asset', 'market')

    def get_free(self, wallet: models.Wallet):
        return float(wallet.get_free())

    get_free.short_description = 'free'

    def get_locked(self, wallet: models.Wallet):
        return float(wallet.get_locked())

    get_locked.short_description = 'locked'

    def get_free_irt(self, wallet: models.Wallet):
        return wallet.asset.get_presentation_price_irt(wallet.get_balance_irt())
    get_free_irt.short_description = 'ارزش ریالی'

    def get_free_usdt(self, wallet: models.Wallet):
        return wallet.asset.get_presentation_price_usdt(wallet.get_balance_usdt())
    get_free_usdt.short_description = 'ارزش دلاری'


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
        'comment': True
    }

    list_display = (
        'created', 'network', 'get_asset', 'amount', 'fee_amount', 'deposit', 'status', 'source', 'get_user',
        'get_total_volume_usdt', 'get_remaining_time_to_pass_72h', 'get_jalali_created'
    )
    search_fields = ('trx_hash', 'block_hash', 'block_number', 'out_address', 'wallet__asset__symbol')
    list_filter = ('deposit', 'status', 'source', 'status', TransferUserFilter,)
    readonly_fields = ('deposit_address', 'network', 'wallet', 'get_total_volume_usdt', 'created', 'accepted_datetime',
                       'finished_datetime', 'get_risks')
    exclude = ('risks', )

    actions = ('accept_withdraw', 'reject_withdraw')

    def save_model(self, request, obj: models.Transfer, form, change):
        if obj.id and obj.status == models.Transfer.DONE and obj.trx_hash:
            old = models.Transfer.objects.get(id=obj.id)

            if old.status != models.Transfer.DONE:
                old.accept(obj.trx_hash)

        obj.save()

    @admin.display(description='ارزش تتری')
    def get_total_volume_usdt(self, transfer: models.Transfer):
        price = get_trading_price_usdt(coin=transfer.wallet.asset.symbol, side=SELL)
        if price:
            return round(transfer.amount * price, 1)

    def get_queryset(self, request):
        queryset = super(TransferAdmin, self).get_queryset(request).select_related('wallet__account__user')

        users = set(queryset.filter(deposit=False).values_list('wallet__account__user_id', flat=True))

        return queryset

    @admin.display(description='Asset')
    def get_asset(self, transfer: models.Transfer):
        return transfer.wallet.asset

    @admin.display(description='created jalali')
    def get_jalali_created(self, transfer: models.Transfer):
        return gregorian_to_jalali_datetime_str(transfer.created)

    @admin.display(description='User')
    def get_user(self, transfer: models.Transfer):
        user = transfer.wallet.account.user

        if user:
            link = url_to_edit_object(user)
            return anchor_tag(user.phone, link)

    @admin.display(description='Remaining 72h')
    def get_remaining_time_to_pass_72h(self, transfer: models.Transfer):
        if transfer.deposit:
            return

        user = transfer.wallet.account.user

        last_payment = Payment.objects.filter(
            created__gt=timezone.now() - timedelta(days=3),
            created__lt=transfer.created,
            status=DONE,
            payment_request__bank_card__user=user
        ).order_by('created').last()

        if last_payment:
            passed = timezone.now() - last_payment.created
            rem = timedelta(days=3) - passed
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


@admin.register(models.Prize)
class PrizeAdmin(admin.ModelAdmin):
    list_display = ('created', 'achievement', 'account', 'get_asset_amount')
    readonly_fields = ('account', 'asset', )

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
    list_display = ('address', )
    readonly_fields = ('address', 'account')
    search_fields = ('address', 'public_address')
    list_filter = ('architecture', )


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
class AssetSnapshotAdmin(admin.ModelAdmin):
    list_display = ('created', 'asset', 'total_amount', 'users_amount', 'hedge_amount', 'hedge_value', 'get_hedge_diff')
    ordering = ('-created', 'asset__order')
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
