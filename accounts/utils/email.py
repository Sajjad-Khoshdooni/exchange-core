import logging

import requests
from django.conf import settings
from django.template.loader import render_to_string
from decouple import config

logger = logging.getLogger(__name__)


SCOPE_VERIFY_EMAIL = 'verify_email'
SCOPE_WITHDRAW_EMAIL = 'withdraw_email'
SCOPE_DEPOSIT_EMAIL = 'deposit_email'
SCOPE_SUCCESSFUL_FIAT_WITHDRAW = 'successful_fiat_withdraw_email'
SCOPE_CANCEL_FIAT_WITHDRAW = 'cancel_fiat_withdraw_email'
SCOPE_PAYMENT = 'payment_email'


SCOPE_MARGIN_UNDER_LIQUIDATION = 'margin_under_liquidation'
SCOPE_MARGIN_LIQUIDATION_FINISHED = 'margin_liquidation_finished'


SCOPE_DONE_STAKE = 'done_stake'

SCOPE_CANCEL_STAKE = 'cancel_stake'

SCOPE_2FA_ACTIVATE = 'activate_2fa'

TEMPLATES = {
    SCOPE_VERIFY_EMAIL: {
        'subject':  '{} | کد تایید ایمیل'.format(settings.BRAND),
        'html': 'accounts/email/verify_email.min.html',
        'text': 'accounts/text/verify_email.txt',
    },
    SCOPE_WITHDRAW_EMAIL: {
        'subject': '{} | اطلاع‌رسانی برداشت رمز ارزی'.format(settings.BRAND),
        'html': 'accounts/email/withdraw_email.min.html',
        'text': 'accounts/text/withdraw_email.txt',
    },
    SCOPE_SUCCESSFUL_FIAT_WITHDRAW: {
        'subject': '{} | اطلاع‌رسانی برداشت ریالی'.format(settings.BRAND),
        'html': 'accounts/email/successful_fiat_withdraw_email.min.html',
        'text': 'accounts/text/successful_fiat_withdraw_email.txt',
    },
    SCOPE_CANCEL_FIAT_WITHDRAW: {
        'subject': '{} | اطلاع‌رسانی لغو برداشت ریالی '.format(settings.BRAND),
        'html': 'accounts/email/cancel_fiat_withdraw_email.min.html',
        'text': 'accounts/text/cancel_fiat_withdraw_email.txt',
    },
    SCOPE_DEPOSIT_EMAIL: {
        'subject': '{} | اطلاع‌رسانی واریز رمزارزی '.format(settings.BRAND),
        'html': 'accounts/email/deposit_email.min.html',
        'text': 'accounts/text/deposit_email.txt',
    },
    SCOPE_PAYMENT: {
        'subject': '{} | اطلاع‌رسانی واریز ریالی'.format(settings.BRAND),
        'html': 'accounts/email/payment_email.min.html',
        'text': 'accounts/text/payment_email.txt',
    },
    SCOPE_MARGIN_LIQUIDATION_FINISHED: {
        'subject': '{} | تسویه خودکار حساب تعهدی'.format(settings.BRAND),
        'html': 'accounts/email/margin_liquidation_finished.min.html',
        'text': 'accounts/text/margin_liquidation_finished.txt',
    },

    SCOPE_2FA_ACTIVATE: {
        'subject': '{} | فعال سازی رمز دوعاملی'.format(settings.BRAND),
        'html': 'accounts/email/activate_2fa_email.min.html',
        'text': 'accounts/text/activate_2fa.txt',
    },

    'cancel_stake': {
        'subject': '{} | اطلاع‌رسانی لغو staking'.format(settings.BRAND),
        'html': 'accounts/email/cancel_staking_email.min.html',
        'text': 'accounts/text/cancel_staking.txt',
    },
    'done_stake': {
            'subject': '{} | اطلاع‌رسانی تایید staking'.format(settings.BRAND),
            'html': 'accounts/email/done_staking_email.min.html',
            'text': 'accounts/text/done_staking.txt',
        },
}


def send_email_by_template(recipient: str, template: str, context: dict = None):
    if not recipient:
        return

    data = TEMPLATES[template]

    body_html = render_to_string(data['html'], context or {})
    body_txt = render_to_string(data['text'], context or {})

    return send_email(
        subject=data['subject'],
        body_html=body_html,
        body_text=body_txt,
        transactional=data.get('transactional', True),
        purpose=template,
        to=[recipient]
    )


def send_email(subject: str, body_html: str, body_text: str, to: list, transactional: bool = True, purpose: str = 'Email'):
    if settings.DEBUG_OR_TESTING_OR_STAGING:
        return print(subject, body_html, body_text, purpose, to)

    resp = requests.post(
        'https://api.elasticemail.com/v2/email/send',
        params={
            'apikey': config('ELASTICMAIL_API_KEY'),
            'subject': subject,
            'bodyHtml': body_html,
            'bodyText': body_text,
            'charset': 'utf-8',
            'from': config('EMAIL_SENDER'),
            'fromName': settings.BRAND,
            'isTransactional': transactional,
            'msgTo': ','.join(to),
            'utmSource': 'ElasticEmail',
            'utmMedium': 'Email',
            'utmContent': settings.BRAND_EN,
            'utmCampaign': purpose,
        }
    )

    data = resp.json()

    if not resp.ok or not data['success']:
        logger.error("Error sending email to elastic", extra={
            'subject': subject,
            'status': resp.status_code,
            'data': data
        })

        print('elasticmail error', data)

    return data
