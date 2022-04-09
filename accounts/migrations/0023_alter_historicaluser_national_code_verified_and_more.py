# Generated by Django 4.0 on 2022-04-03 12:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0022_historicaluser_archived_user_archived'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicaluser',
            name='national_code_verified',
            field=models.BooleanField(blank=True, db_index=True, null=True, verbose_name='تاییدیه کد ملی'),
        ),
        migrations.AlterField(
            model_name='user',
            name='national_code_verified',
            field=models.BooleanField(blank=True, db_index=True, null=True, verbose_name='تاییدیه کد ملی'),
        ),
        migrations.AlterField(
            model_name='verificationcode',
            name='scope',
            field=models.CharField(choices=[('forget', 'forget'), ('verify', 'verify'), ('withdraw', 'withdraw'), ('tel', 'tel'), ('change_pass', 'change_pass')], max_length=16),
        ),
    ]