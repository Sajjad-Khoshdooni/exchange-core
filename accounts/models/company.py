from enum import Enum
import json

from django.db import models

from accounts.verifiers.finotech import ServerError
from accounts.verifiers.zibal import ZibalRequester
from accounts.validators import company_national_id_validator

import logging

logger = logging.getLogger(__name__)


class State(Enum):
    INITIALIZED = 'initial'
    PENDING = 'pending'
    INFORMATION_NO_FETCHED = 'company_information_not_fetched'
    REJECTED = 'rejected'
    VERIFIED = 'verified'


class Company(models.Model):
    name = models.CharField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    postal_code = models.CharField(null=True, blank=True)
    registration_id = models.CharField(null=True, blank=True, unique=True)
    company_registration_date = models.DateField(null=True, blank=True)
    national_id = models.CharField(validators=[company_national_id_validator], unique=True)
    company_documents = models.OneToOneField(
        to='multimedia.File',
        on_delete=models.PROTECT,
        verbose_name='مدارک شرکت',
        related_name='+',
        blank=True,
        null=True
    )
    fetched_data = models.JSONField(null=True, blank=True)
    is_active = models.BooleanField(null=True, blank=True)
    docs_state = models.CharField(choices=[(tag.name, tag.value) for tag in State], default=State.INITIALIZED)
    information_state = models.CharField(choices=[(tag.name, tag.value) for tag in State], default=State.INITIALIZED)

    @property
    def is_verified(self):
        return self.docs_state == State.VERIFIED and self.information_state == State.VERIFIED

    def verify_and_fetch_company_data(self, retry: int = 2):
        requester = ZibalRequester(user=self.user)
        try:
            data = requester.company_information(self.national_id).data
            if data.code == "SUCCESSFUL":
                self.name = data.title
                self.address = data.address
                self.postal_code = data.postal_code
                self.registration_id = data.registration_id
                self.is_active = data.status == 'فعال'
                self.fetched_data = json.dumps(data, default=lambda o: o.__dict__)
                self.save(update_fields=['name, address', 'postal_code', 'registration_id', 'fetched_data', 'is_active'])
        except (TimeoutError, ServerError):
            if retry == 0:
                logger.error('company information retrieval timeout')
                return
            else:
                logger.info('Retrying company information fetching..')
                return self.verify_and_fetch_company_data(retry - 1)

    class Meta:
        verbose_name = 'شرکت'
        verbose_name_plural = 'شرکت‌ها'
