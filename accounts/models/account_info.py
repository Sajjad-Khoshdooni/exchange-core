from django.db import models, transaction

from accounts.models import User
from ledger.utils.fields import get_group_id_field


class VerifiableField(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(to=User, on_delete=models.CASCADE)

    name = models.CharField(max_length=64)
    value = models.CharField(max_length=512)

    verified_date = models.DateTimeField(null=True, blank=True)
    verified = models.BooleanField(default=False)

    group_id = get_group_id_field(db_index=True)

    class Meta:
        unique_together = ('user', 'name', 'value')

    def insert(self, user: User, field_names: list):
        objects = [VerifiableField(user=user, name=name) for name in field_names]
        return VerifiableField.objects.bulk_create(objects)


class BasicAccountInfo(models.Model):
    MALE = 'm'
    FEMALE = 'f'

    INIT, PENDING, REJECTED, VERIFIED = 'init', 'pending', 'rejected', 'verified'

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    user = models.OneToOneField(to=User, on_delete=models.PROTECT)

    status = models.CharField(
        max_length=8,
        choices=((INIT, INIT), (PENDING, PENDING), (REJECTED, REJECTED), (VERIFIED, VERIFIED)),
        default=INIT,
    )

    birth_date = models.DateField(null=True, blank=True)

    group_id = get_group_id_field()

    def verify(self):
        assert self.status in (self.INIT, self.REJECTED)

        with transaction.atomic():
            self.status = self.PENDING
            self.save()

            fields = []

            VerifiableField.insert(self.user, field_names=[
                'first_name', 'last'
            ])

    def __str__(self):
        return '%s (%s)' % (self.user, self.status)

    def save(self, *args, **kwargs):
        super(BasicAccountInfo, self).save(*args, **kwargs)

        if self.status == self.VERIFIED and self.user.verification < User.BASIC_VERIFIED:
            self.user.verification = User.BASIC_VERIFIED
            self.user.save()

        if self.status != self.VERIFIED and self.user.verification == User.BASIC_VERIFIED:
            self.user.verification = User.NOT_VERIFIED
            self.user.save()


def verify_national_code(user: User):
    assert not user.national_code_verified

    
