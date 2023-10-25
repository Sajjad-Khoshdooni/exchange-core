from enum import Enum

from django.db import models

from accounts.validators import company_national_id_validator


class CompanyState(Enum):
    INITIAL = 'initial'
    PARTIALLY_VERIFIED = 'partially_verified'
    FULLY_VERIFIED = 'verified'


class Company(models.Model):
    name = models.CharField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    postal_code = models.PositiveIntegerField(null=True, blank=True)
    registration_number = models.PositiveIntegerField(null=True, blank=True, unique=True)
    company_registration_date = models.DateField(null=True, blank=True)
    national_id = models.CharField(validators=[company_national_id_validator], unique=True)
    state = models.CharField(choices=[(tag.name, tag.value) for tag in CompanyState])

    class Meta:
        verbose_name = 'شرکت'
        verbose_name_plural = 'شرکت‌ها'

