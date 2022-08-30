# Generated by Django 4.0 on 2022-08-29 09:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0057_auto_20220822_1719'),
    ]

    operations = [
        migrations.CreateModel(
            name='FiatHedgeTrx',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('base_amount', models.DecimalField(decimal_places=8, max_digits=30)),
                ('target_amount', models.DecimalField(decimal_places=8, max_digits=30)),
                ('price', models.DecimalField(decimal_places=8, max_digits=30)),
                ('source', models.CharField(choices=[('t', 'trade'), ('m', 'manual')], max_length=1)),
                ('reason', models.CharField(blank=True, max_length=64)),
            ],
        ),
    ]
