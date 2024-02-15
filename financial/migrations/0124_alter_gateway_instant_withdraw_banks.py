# Generated by Django 4.1.3 on 2024-02-13 11:13

from django.db import migrations, models
import financial.utils.admin


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0123_novinpalgateway_alter_gateway_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gateway',
            name='instant_withdraw_banks',
            field=financial.utils.admin.MultiSelectArrayField(base_field=models.CharField(choices=[('MELLI', 'MELLI'), ('REFAH', 'REFAH'), ('RESALAT', 'RESALAT'), ('KESHAVARZI', 'KESHAVARZI'), ('TOSEAH_TAAVON', 'TOSEAH_TAAVON'), ('SADERAT', 'SADERAT'), ('KARAFARIN', 'KARAFARIN'), ('EGHTESAD_NOVIN', 'EGHTESAD_NOVIN'), ('SHAHR', 'SHAHR'), ('SEPAH', 'SEPAH'), ('MEHR_IRAN', 'MEHR_IRAN'), ('PASARGAD', 'PASARGAD'), ('NOOR', 'NOOR'), ('SARMAYEH', 'SARMAYEH'), ('MELAL', 'MELAL'), ('MASKAN', 'MASKAN'), ('POST', 'POST'), ('KHAVARMIANEH', 'KHAVARMIANEH'), ('SINA', 'SINA'), ('MELLAT', 'MELLAT'), ('IRANZAMIN', 'IRANZAMIN'), ('DAY', 'DAY'), ('AYANDEH', 'AYANDEH'), ('GARDESHGARI', 'GARDESHGARI'), ('SAMAN', 'SAMAN'), ('TEJARAT', 'TEJARAT'), ('PARSIAN', 'PARSIAN'), ('SANAT_VA_MADAN', 'SANAT_VA_MADAN')], max_length=16), blank=True, default=[], size=None),
        ),
    ]