import logging
from dataclasses import dataclass

import requests
from decouple import config
from django.conf import settings
from django.template import loader

logger = logging.getLogger(__name__)


def send_raw_email_by_template(email: str, template: str, context: dict = None):
    email_info = load_email_template(template, context)

    send_email(
        subject=email_info.title,
        body_html=email_info.body_html,
        body_text=email_info.body,
        to=[email],
    )


def send_email(subject: str, body_html: str, body_text: str, to: list, transactional: bool = True,
               purpose: str = 'Notification'):

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
        },
        timeout=30,
    )

    data = resp.json()

    if not resp.ok or not data['success']:
        logger.error("Error sending email to elastic", extra={
            'subject': subject,
            'status': resp.status_code,
            'data': data
        })

        logger.info('elasticmail error', data)
        return

    return data


@dataclass
class EmailInfo:
    title: str
    body: str
    body_html: str


def load_email_template(template: str, context: dict = None) -> EmailInfo:
    body_html = loader.render_to_string(
        f'accounts/notif/email/{template}/body.html',
        context=context)

    body = loader.render_to_string(
        f'accounts/notif/email/{template}/body.txt',
        context=context)

    title = loader.render_to_string(f'accounts/notif/email/{template}/title.txt') + ' | ' + settings.BRAND

    return EmailInfo(
        title=title,
        body=body,
        body_html=body_html,
    )
