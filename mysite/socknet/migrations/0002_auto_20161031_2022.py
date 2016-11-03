# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-11-01 02:22
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('socknet', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='author',
            name='about_me',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AddField(
            model_name='author',
            name='birthday',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='author',
            name='github_url',
            field=models.TextField(blank=True),
        ),
    ]