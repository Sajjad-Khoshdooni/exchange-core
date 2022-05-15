import logging

import requests
from django.conf import settings
from django.template.loader import render_to_string
from yekta_config import secret
from yekta_config.config import config

logger = logging.getLogger(__name__)


api_key = secret('ELASTICMAIL_API_KEY')
email_sender = config('EMAIL_SENDER')
brand = config('BRAND')


TEMPLATES = {
    'verify_email': {
        'subject': 'راستین | کد تایید ایمیل',
        'html': 'accounts/email/verify_email.min.html',
        'text': 'accounts/text/verify_email.txt',
    }
}


def send_email_by_template(recipient: str, template: str, context: dict = None):
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

    resp = requests.post(
        'https://api.elasticemail.com/v2/email/send',
        params={
            'apikey': api_key,
            'subject': subject,
            'bodyHtml': body_html,
            'bodyText': body_text,
            'charset': 'utf-8',
            'from': email_sender,
            'fromName': brand,
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
