# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-05-11 16:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('report', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='testcase',
            name='suite',
            field=models.CharField(max_length=32),
        ),
    ]