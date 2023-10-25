from enum import Enum

from django.db import models

from accounts.validators import company_national_id_validator


class CompanyState(Enum):
    INITIALIZED = 'initial'
    PENDING = 'pending'
    DOCS_REJECTED = 'docs_rejected'
    WRONG_NATIONAL_ID = 'wrong_national_id'
    VERIFIED = 'verified'


class Company(models.Model):
    name = models.CharField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    postal_code = models.PositiveIntegerField(null=True, blank=True)
    registration_number = models.PositiveIntegerField(null=True, blank=True, unique=True)
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
    state = models.CharField(choices=[(tag.name, tag.value) for tag in CompanyState], default=CompanyState.INITIALIZED)

    class Meta:
        verbose_name = 'شرکت'
        verbose_name_plural = 'شرکت‌ها'
