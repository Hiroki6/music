# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-12-26 17:20
from __future__ import unicode_literals

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('recommendation', '0016_auto_20161222_2219'),
    ]

    operations = [
        migrations.CreateModel(
            name='ComparisonSearchType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('search_type', models.CharField(max_length=50)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterField(
            model_name='emotionemotionbasedsong',
            name='created_at',
            field=models.DateTimeField(default=datetime.datetime(2016, 12, 27, 2, 20, 8, 512889)),
        ),
        migrations.AlterField(
            model_name='emotionemotionbasedsong',
            name='updated_at',
            field=models.DateTimeField(default=datetime.datetime(2016, 12, 27, 2, 20, 8, 512916)),
        ),
        migrations.AlterField(
            model_name='emotionrelevantsong',
            name='created_at',
            field=models.DateTimeField(default=datetime.datetime(2016, 12, 27, 2, 20, 8, 512095)),
        ),
        migrations.AlterField(
            model_name='emotionrelevantsong',
            name='updated_at',
            field=models.DateTimeField(default=datetime.datetime(2016, 12, 27, 2, 20, 8, 512125)),
        ),
        migrations.AlterField(
            model_name='searchsong',
            name='created_at',
            field=models.DateTimeField(default=datetime.datetime(2016, 12, 27, 2, 20, 8, 515167)),
        ),
        migrations.AlterField(
            model_name='searchsong',
            name='updated_at',
            field=models.DateTimeField(default=datetime.datetime(2016, 12, 27, 2, 20, 8, 515198)),
        ),
    ]
