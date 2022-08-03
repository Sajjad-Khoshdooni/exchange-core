# Generated by Django 4.0 on 2022-07-26 09:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0109_merge_20220726_1230'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='wallet',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='wallet',
            constraint=models.UniqueConstraint(condition=models.Q(('variant__isnull', True)), fields=('account', 'asset', 'market'), name='uniqueness_without_variant_constraint'),
        ),
        migrations.AddConstraint(
            model_name='wallet',
            constraint=models.UniqueConstraint(condition=models.Q(('variant__isnull', False)), fields=('account', 'asset', 'market', 'variant'), name='uniqueness_with_variant_constraint'),
        ),
    ]
