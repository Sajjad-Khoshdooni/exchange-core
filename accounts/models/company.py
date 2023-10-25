from django.db import models

from accounts.validators import company_national_id_validator


class Company(models.Model):
    national_id = models.CharField(validators=[company_national_id_validator], unique=True)
