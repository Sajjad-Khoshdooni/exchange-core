# Generated by Django 4.1.3 on 2023-07-10 12:17

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


def populate_payment_fields(apps, schema_editor):
    Payment = apps.get_model('financial', 'Payment')
    PaymentRequest = apps.get_model('financial', 'PaymentRequest')
    PaymentIdRequest = apps.get_model('financial', 'PaymentIdRequest')

    for payment in Payment.objects.filter(payment_request__isnull=False).select_related('paymentrequest__bank_card'):
        req = payment.payment_request
        payment.user = req.bank_card.user
        payment.amount = req.amount
        payment.fee = req.fee
        payment.save(update_fields=['user', 'amount', 'fee'])

        payment.payment_request.payment = payment
        payment.payment_request.group_id = payment.group_id
        payment.payment_request.save(update_fields=['payment', 'group_id'])

    # for payment_request in PaymentRequest.objects.filter(payment__isnull=True):
    #     payment_request.group_id = uuid.uuid4()
    #     payment_request.save(update_fields=['group_id'])

    for payment in Payment.objects.filter(payment_id_request__isnull=False).select_related('paymentidrequest__owner'):
        req = payment.payment_id_request
        payment.user = req.owner.user
        payment.amount = req.amount
        payment.fee = req.fee
        payment.save(update_fields=['user', 'amount', 'fee'])

        payment.payment_request.payment = payment
        payment.payment_id_request.group_id = payment.group_id
        payment.payment_id_request.save(update_fields=['payment', 'group_id'])

    # for payment_id_request in PaymentIdRequest.objects.filter(payment__isnull=True):
    #     payment_id_request.group_id = uuid.uuid4()
    #     payment_id_request.save(update_fields=['group_id'])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('financial', '0091_alter_gateway_type'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='payment',
            name='check_financial_payment_requests',
        ),
        migrations.RenameField(
            model_name='paymentidrequest',
            old_name='payment_id',
            new_name='owner',
        ),
        migrations.AddField(
            model_name='payment',
            name='amount',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='payment',
            name='fee',
            field=models.PositiveIntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='payment',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='paymentidrequest',
            name='group_id',
            field=models.UUIDField(default=uuid.uuid4),
        ),
        migrations.AddField(
            model_name='paymentidrequest',
            name='payment',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='financial.payment'),
        ),
        migrations.AddField(
            model_name='paymentrequest',
            name='group_id',
            field=models.UUIDField(default=uuid.uuid4),
        ),
        migrations.AddField(
            model_name='paymentrequest',
            name='payment',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='financial.payment'),
        ),
        migrations.AlterField(
            model_name='payment',
            name='group_id',
            field=models.UUIDField(default=None),
        ),

        migrations.RunPython(
            code=populate_payment_fields,
            reverse_code=migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name='payment',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                    to=settings.AUTH_USER_MODEL),
        ),
        migrations.RemoveField(
            model_name='payment',
            name='payment_id_request',
        ),
        migrations.RemoveField(
            model_name='payment',
            name='payment_request',
        ),
    ]
