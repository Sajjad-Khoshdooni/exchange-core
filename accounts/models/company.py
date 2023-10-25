from enum import Enum
import json

from django.db import models

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
    name = models.CharField(null=True, blank=True, max_length=128)
    address = models.TextField(null=True, blank=True)
    postal_code = models.CharField(null=True, blank=True, max_length=128)
    registration_id = models.CharField(null=True, blank=True, unique=True, max_length=128)
    company_registration_date = models.CharField(null=True, blank=True, max_length=128)
    national_id = models.CharField(validators=[company_national_id_validator], unique=True, max_length=10)
    is_active = models.BooleanField(null=True, blank=True, default=False)
    company_documents = models.OneToOneField(
        to='multimedia.File',
        on_delete=models.PROTECT,
        verbose_name='مدارک شرکت',
        related_name='+',
        blank=True,
        null=True
    )
    fetched_data = models.JSONField(null=True, blank=True)
    docs_state = models.CharField(choices=[(tag.name, tag.value) for tag in State], default=State.INITIALIZED,
                                  max_length=128)
    information_state = models.CharField(choices=[(tag.name, tag.value) for tag in State], default=State.INITIALIZED,
                                         max_length=128)

    is_verified = models.BooleanField(null=True, blank=True, default=False)

    def verify_and_fetch_company_data(self, retry: int = 2):
        from accounts.verifiers.finotech import ServerError
        from accounts.verifiers.zibal import ZibalRequester
        requester = ZibalRequester(user=self.user)
        try:
            data = requester.company_information(self.national_id).data
            if data.code == "SUCCESSFUL":
                self.name = data.title
                self.address = data.address
                self.postal_code = data.postal_code
                self.registration_id = data.registration_id
                self.is_active = data.status == 'فعال'
                self.company_registration_date = data.establishment_date
                self.fetched_data = json.dumps(data, default=lambda o: o.__dict__)
                self.save(
                    update_fields=['name, address', 'postal_code', 'registration_id', 'fetched_data', 'is_active',
                                   'company_registration_date',])
        except (TimeoutError, ServerError):
            if retry == 0:
                logger.error('company information retrieval timeout')
                return
            else:
                logger.info('Retrying company information fetching..')
                return self.verify_and_fetch_company_data(retry - 1)

    def accept(self):
        self.is_verified = True
        self.save(update_fields=['is_verified'])

    def reject(self):
        self.is_verified = False
        self.save(update_fields=['is_verified'])

    class Meta:
        verbose_name = 'شرکت'
        verbose_name_plural = 'شرکت‌ها'
