from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User, Notification
from ledger.models import Prize, Transfer


AUTH, DEPOSIT, TRADE = 'auth', 'deposit', 'trade'


ALERTS = {
    AUTH: {
        'text': "با تکمیل احراز هویت، بدون محدودیت در راستین خرید و فروش کنید.",
        'btn_link': "/account/verification/basic",
        'btn_title': "احراز هویت",
        'level': Notification.ERROR
    },
    DEPOSIT: {
        'text': "با واریز وجه، تنها چند ثانیه با خرید و فروش رمزارز فاصله دارید.",
        'btn_link': "/wallet/spot/money-deposit",
        'btn_title': "واریز",
        'level': Notification.WARNING
    },
    TRADE: {
        'text': "به ارزش ۲ میلیون تومان معامله کنید و ۵۰,۰۰۰ شیبا جایزه بگیرید.",
        'btn_link': "/trade/classic/BTCUSDT",
        'btn_title': "شروع معامله",
        'level': Notification.INFO
    },
}


class BannerAlertAPIView(APIView):
    def get(self, request):
        condition = self.get_alert_condition()
        data = ALERTS.get(condition)

        return Response({
            'banner': data
        })

    def get_alert_condition(self):
        user = self.request.user

        if 0 < user.account.trade_volume_irt < Prize.TRADE_THRESHOLD_2M:
            return TRADE

        elif user.account.trade_volume_irt == 0:
            has_deposit = user.first_fiat_deposit_date or \
                          Transfer.objects.filter(wallet__account=user.account, deposit=True, status=Transfer.DONE)

            if has_deposit:
                return TRADE

            elif user.level == User.LEVEL1:
                return AUTH
            else:
                return DEPOSIT
