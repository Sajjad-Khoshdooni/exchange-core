from django.db import transaction

from accounts.models import Account, Notification
from ledger.models import Prize, Asset
from ledger.models.asset import AssetSerializerMini
from ledger.utils.precision import humanize_number
from ledger.utils.price import get_trading_price_usdt, SELL
from ledger.utils.wallet_pipeline import WalletPipeline


class Achievement:
    def __init__(self, account: Account):
        self.account = account

    def as_dict(self):
        raise NotImplementedError

    def achieve_prize(self):
        raise NotImplementedError

    def achieved(self):
        raise NotImplementedError


class PrizeAchievement(Achievement):
    scope = None

    def as_dict(self):
        prize = Prize.objects.filter(account=self.account, scope=self.scope).first()

        if prize:
            amount = prize.amount
        else:
            amount = Prize.PRIZE_AMOUNTS[self.scope]

        shib = Asset.get(symbol=Asset.SHIB)

        return {
            'type': 'prize',
            'id': prize and prize.id,
            'scope': self.scope,
            'amount': amount,
            'asset': AssetSerializerMini(shib).data,
            'achieved': bool(prize),
            'redeemed': bool(prize) and prize.redeemed,
            'fake': bool(prize) and prize.fake,
        }

    def achieved(self):
        return Prize.objects.filter(account=self.account, scope=self.scope).exists()


class TradePrizeAchievementStep1(PrizeAchievement):
    scope = Prize.TRADE_PRIZE_STEP1

    def achieve_prize(self):
        price = get_trading_price_usdt(Asset.SHIB, SELL, raw_price=True)

        with WalletPipeline() as pipeline:
            prize, _ = Prize.objects.get_or_create(
                account=self.account,
                scope=Prize.TRADE_PRIZE_STEP1,
                defaults={
                    'amount': Prize.PRIZE_AMOUNTS[Prize.TRADE_PRIZE_STEP1],
                    'asset': Asset.get(Asset.SHIB),
                    'value': Prize.PRIZE_AMOUNTS[Prize.TRADE_PRIZE_STEP1] * price
                }
            )

            title = 'جایزه به شما تعلق گرفت.'
            description = 'جایزه {} شیبا به شما تعلق گرفت. برای دریافت جایزه، کلیک کنید.'.format(
                humanize_number(prize.asset.get_presentation_amount(prize.amount))
            )

            Notification.send(
                recipient=self.account.user,
                title=title,
                message=description,
                level=Notification.SUCCESS,
                link='/account/tasks'
            )

            if self.account.referred_by:
                price = get_trading_price_usdt(Asset.SHIB, SELL, raw_price=True)

                prize, created = Prize.objects.get_or_create(
                    account=self.account.referred_by.owner,
                    scope=Prize.REFERRAL_TRADE_2M_PRIZE,
                    variant=str(self.account.id),
                    defaults={
                        'amount': Prize.PRIZE_AMOUNTS[Prize.REFERRAL_TRADE_2M_PRIZE],
                        'asset': Asset.get(Asset.SHIB),
                        'value': Prize.PRIZE_AMOUNTS[Prize.REFERRAL_TRADE_2M_PRIZE] * price
                    }
                )

                if created:
                    prize.build_trx(pipeline)


class TradePrizeAchievementStep2(PrizeAchievement):
    scope = Prize.TRADE_PRIZE_STEP2

    def achieve_prize(self):
        price = get_trading_price_usdt(Asset.SHIB, SELL, raw_price=True)

        with transaction.atomic():
            prize, _ = Prize.objects.get_or_create(
                account=self.account,
                scope=Prize.TRADE_PRIZE_STEP2,
                defaults={
                    'amount': Prize.PRIZE_AMOUNTS[Prize.TRADE_PRIZE_STEP2],
                    'asset': Asset.get(Asset.SHIB),
                    'value': Prize.PRIZE_AMOUNTS[Prize.TRADE_PRIZE_STEP2] * price
                }
            )

            title = 'جایزه به شما تعلق گرفت.'
            description = 'جایزه {} شیبا به شما تعلق گرفت. برای دریافت جایزه، کلیک کنید.'.format(
                humanize_number(prize.asset.get_presentation_amount(prize.amount))
            )

            Notification.send(
                recipient=self.account.user,
                title=title,
                message=description,
                level=Notification.SUCCESS,
                link='/account/tasks'
            )


class VerifyPrizeAchievement(PrizeAchievement):
    scope = Prize.VERIFY_PRIZE

    def achieve_prize(self):
        price = get_trading_price_usdt(Asset.SHIB, SELL, raw_price=True)

        with transaction.atomic():
            prize, _ = Prize.objects.get_or_create(
                account=self.account,
                scope=Prize.VERIFY_PRIZE,
                defaults={
                    'amount': Prize.PRIZE_AMOUNTS[Prize.VERIFY_PRIZE],
                    'asset': Asset.get(Asset.SHIB),
                    'value': Prize.PRIZE_AMOUNTS[Prize.VERIFY_PRIZE] * price
                }
            )

            title = 'جایزه به شما تعلق گرفت.'
            description = 'جایزه {} شیبا به شما تعلق گرفت. برای دریافت جایزه، کلیک کنید.'.format(
                humanize_number(prize.asset.get_presentation_amount(prize.amount))
            )

            Notification.send(
                recipient=self.account.user,
                title=title,
                message=description,
                level=Notification.SUCCESS,
                link='/account/tasks'
            )

