# Generated by Django 4.1.3 on 2023-11-22 09:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0226_alter_trx_scope_tokenrebrand'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='feedbackcategory',
            options={'ordering': ('order',), 'verbose_name': 'دسته\u200cبندی بازخورد برداشت', 'verbose_name_plural': 'دسته\u200cبندی\u200cهای بازخورد برداشت'},
        ),
        migrations.AddField(
            model_name='feedbackcategory',
            name='order',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
