# Generated by Django 4.1.3 on 2023-09-23 11:20

from django.db import migrations, models
import django.db.models.deletion
import django_quill.fields


class Migration(migrations.Migration):

    dependencies = [
        ('multimedia', '0008_historicalcoinpricecontent'),
    ]

    operations = [
        migrations.CreateModel(
            name='BaseItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=30)),
                ('title_en', models.CharField(max_length=30)),
                ('slug', models.SlugField(editable=False, max_length=255, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Section',
            fields=[
                ('baseitem_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='multimedia.baseitem')),
                ('description', models.TextField(blank=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='multimedia.section')),
            ],
            bases=('multimedia.baseitem',),
        ),
        migrations.CreateModel(
            name='Article',
            fields=[
                ('baseitem_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='multimedia.baseitem')),
                ('is_pinned', models.BooleanField(default=False)),
                ('content', django_quill.fields.QuillField()),
                ('parent_section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='multimedia.section')),
            ],
            bases=('multimedia.baseitem',),
        ),
    ]
