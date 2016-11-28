# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-11-27 23:20
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('socknet', '0007_auto_20161127_0429'),
    ]

    operations = [
        migrations.CreateModel(
            name='ForeignComment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('content', models.TextField(max_length=512)),
                ('created_on', models.DateTimeField(auto_now=True)),
                ('markdown', models.BooleanField()),
                ('foreign_author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='foreign_comment_author', to='socknet.ForeignAuthor')),
                ('parent_post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='foreign_comment_parent_post', to='socknet.Post')),
            ],
        ),
    ]
