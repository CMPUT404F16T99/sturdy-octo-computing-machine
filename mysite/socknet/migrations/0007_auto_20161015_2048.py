# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-10-15 20:48
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('socknet', '0006_auto_20161015_2034'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='author',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='author', to='socknet.Author'),
        ),
    ]
