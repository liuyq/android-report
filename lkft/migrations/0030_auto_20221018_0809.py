# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2022-10-18 08:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lkft', '0029_auto_20220706_0502'),
    ]

    operations = [
        migrations.AlterField(
            model_name='testcase',
            name='name',
            field=models.CharField(db_index=True, max_length=320),
        ),
    ]
