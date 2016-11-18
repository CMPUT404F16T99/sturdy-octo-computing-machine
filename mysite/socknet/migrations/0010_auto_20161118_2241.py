# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-11-18 22:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('socknet', '0009_foreignauthor_display_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='author',
            name='foreign_friends_im_following',
            field=models.ManyToManyField(blank=True, related_name='foreign_friends_im_following', to='socknet.ForeignAuthor'),
        ),
        migrations.AddField(
            model_name='foreignauthor',
            name='url',
            field=models.URLField(default=b''),
        ),
        migrations.AlterField(
            model_name='node',
            name='url',
            field=models.CharField(max_length=128, unique=True),
        ),
    ]