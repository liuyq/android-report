# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2021-04-14 15:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lkft', '0025_auto_20210413_1307'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportjob',
            name='environment',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
