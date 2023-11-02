# Generated by Django 4.1.3 on 2023-10-25 15:00

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('multimedia', '0020_alter_article_content'),
    ]

    operations = [
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('file', models.FileField(upload_to='')),
            ],
        ),
    ]
