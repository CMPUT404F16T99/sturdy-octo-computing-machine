# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-11-20 18:43
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('socknet', '0016_auto_20161120_1141'),
    ]

    operations = [
        migrations.RenameField(
            model_name='node',
            old_name='user',
            new_name='foreignUserAccessAccount',
        ),
    ]
