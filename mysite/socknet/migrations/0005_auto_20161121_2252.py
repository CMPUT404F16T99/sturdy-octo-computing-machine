# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-11-21 22:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('socknet', '0004_auto_20161121_1929'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='post',
            name='author',
        ),
        migrations.AddField(
            model_name='post',
            name='author_id',
            field=models.UUIDField(default='1f018e19-3c52-404c-b847-d690abb542ad'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='post',
            name='author_name',
            field=models.CharField(default=123, max_length=150),
            preserve_default=False,
        ),
    ]