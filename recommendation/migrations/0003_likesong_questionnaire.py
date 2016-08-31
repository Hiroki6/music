# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-08-31 05:08
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('recommendation', '0002_recommendsong'),
    ]

    operations = [
        migrations.CreateModel(
            name='LikeSong',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recommend_type', models.IntegerField()),
                ('song', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='recommendation.Song')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Questionnaire',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comparison', models.IntegerField()),
                ('interaction_rate', models.IntegerField()),
                ('recommend_rate', models.IntegerField()),
                ('song_nums', models.IntegerField()),
                ('compare_method', models.IntegerField()),
                ('free_content', models.CharField(blank=True, max_length=255, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
