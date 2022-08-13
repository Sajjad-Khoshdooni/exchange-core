# Generated by Django 4.0 on 2022-08-10 09:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0048_remove_bankaccount_unique_bank_account_iban_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='bankaccount',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted', False)), fields=('iban', 'user'), name='unique_bank_account_iban'),
        ),
        migrations.AddConstraint(
            model_name='bankcard',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted', False)), fields=('card_pan', 'user'), name='unique_bank_card_card_pan'),
        ),
    ]
