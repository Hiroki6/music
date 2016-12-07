# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-11-01 02:14
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('recommendation', '0005_auto_20161025_1035'),
    ]

    operations = [
        migrations.CreateModel(
            name='SituationEmotion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('situation', models.IntegerField()),
                ('emotion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='recommendation.Cluster')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]