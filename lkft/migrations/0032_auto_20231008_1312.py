# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2023-10-08 13:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lkft', '0031_auto_20221102_1319'),
    ]

    operations = [
        migrations.AlterField(
            model_name='testcase',
            name='id',
            field=models.BigAutoField(primary_key=True, serialize=False),
        ),
    ]