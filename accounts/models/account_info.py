import requests
from django.conf import settings
from django.db import models

from accounts.models import User
from accounts.utils import gregorian_to_jalali_date
from accounts.validators import national_card_code_validator


class BasicAccountInfo(models.Model):
    MALE = 'm'
    FEMALE = 'f'

    INIT, PENDING, REJECTED, VERIFIED = 'init', 'pending', 'rejected', 'verified'

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    user = models.OneToOneField(to=User, on_delete=models.PROTECT)
    verifier_code = models.CharField(max_length=16, blank=True)

    status = models.CharField(
        max_length=8,
        choices=((INIT, INIT), (PENDING, PENDING), (REJECTED, REJECTED), (VERIFIED, VERIFIED)),
        default=INIT,
    )

    gender = models.CharField(
        max_length=1,
        choices=((MALE, MALE), (FEMALE, FEMALE))
    )

    birth_date = models.DateField()

    national_card_code = models.CharField(
        max_length=10,
        validators=[national_card_code_validator],
    )

    national_card_image = models.ForeignKey(to='multimedia.Image', on_delete=models.PROTECT)

    def verify(self):
        assert self.status in (self.INIT, self.REJECTED)

        resp = requests.get('https://inquery.ir/:70', params={
            'Token': settings.SEARCHLINE_TOKEN,
            'IdCode': self.national_card_code,
            'BirthDate': gregorian_to_jalali_date(self.birth_date).strftime('%Y/%m/%d'),
            'Name': self.user.first_name,
            'Family': self.user.last_name,
            'Photo': self.national_card_image.get_absolute_image_url(),
        })

        self.verifier_code = resp.json()['Result']['ID']
        self.status = self.PENDING
        self.save()

    def __str__(self):
        return '%s (%s)' % (self.user, self.status)

    def save(self, *args, **kwargs):
        super(BasicAccountInfo, self).save(*args, **kwargs)

        if self.status == self.VERIFIED and self.user.verification < User.BASIC_VERIFIED:
            self.user.verification = User.BASIC_VERIFIED
            self.user.save()
