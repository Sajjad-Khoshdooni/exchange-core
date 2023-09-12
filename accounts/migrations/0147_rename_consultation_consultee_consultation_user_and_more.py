# Generated by Django 4.1.3 on 2023-09-12 08:03

from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0146_consultation'),
    ]

    operations = [
        migrations.RenameField(
            model_name='consultation',
            old_name='consultee',
            new_name='user',
        ),
        migrations.AlterField(
            model_name='consultation',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL,
                                    verbose_name='کاربر'),
        ),
        migrations.AlterField(
            model_name='consultation',
            name='consulter',
            field=models.ForeignKey(blank=True, limit_choices_to={'is_staff': True}, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='consulters', to=settings.AUTH_USER_MODEL, verbose_name='مشاور'),
        ),
        migrations.AlterField(
            model_name='consultation',
            name='status',
            field=models.CharField(choices=[('process', 'در حال پردازش'), ('pending', 'در انتظار تایید'), ('canceled', 'لغو شده'), ('done', 'انجام شده')], default='pending', max_length=8),
        ),
    ]
