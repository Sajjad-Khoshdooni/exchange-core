# Generated by Django 4.1.3 on 2023-10-19 06:53

from django.db import migrations, models
import django.db.models.deletion
import django_quill.fields


class Migration(migrations.Migration):

    dependencies = [
        ('multimedia', '0017_remove_article_baseitem_ptr_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.TextField(max_length=256)),
                ('title_en', models.TextField(max_length=256)),
                ('slug', models.SlugField(blank=True, max_length=1024, unique=True)),
                ('is_pinned', models.BooleanField(default=False)),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('content', django_quill.fields.QuillField()),
            ],
            options={
                'verbose_name': 'مقاله',
                'verbose_name_plural': 'مقاله\u200cها',
                'ordering': ('order', 'id'),
            },
        ),
        migrations.CreateModel(
            name='Section',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.TextField(max_length=256)),
                ('title_en', models.TextField(max_length=256)),
                ('slug', models.SlugField(blank=True, max_length=1024, unique=True)),
                ('description', models.TextField(blank=True)),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('icon', models.CharField(blank=True, choices=[('getting-started', 'getting-started'), ('signup', 'signup'), ('accounts', 'accounts'), ('transfer', 'transfer'), ('trade', 'trade'), ('earn', 'earn')], max_length=256)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='multimedia.section')),
            ],
            options={
                'verbose_name': 'بخش',
                'verbose_name_plural': 'بخش\u200c\u200cها',
                'ordering': ('order', 'id'),
            },
        ),
        migrations.AddField(
            model_name='article',
            name='parent',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='multimedia.section'),
        ),
    ]