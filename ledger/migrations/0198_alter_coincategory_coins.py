# Generated by Django 4.1.3 on 2023-07-31 11:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0197_alter_coincategory_options_coincategory_description_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coincategory',
            name='coins',
            field=models.ManyToManyField(blank=True, to='ledger.asset'),
        ),
    ]