# Generated by Django 4.1.3 on 2023-10-22 15:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('multimedia', '0018_article_section_delete_baseitem_article_parent'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='_content_html',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='article',
            name='_content_text',
            field=models.TextField(blank=True),
        ),
    ]
