# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2021-04-12 08:43
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lkft', '0023_reportbuild_finished'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportproject',
            name='is_archived',
            field=models.BooleanField(default=True),
        ),
    ]