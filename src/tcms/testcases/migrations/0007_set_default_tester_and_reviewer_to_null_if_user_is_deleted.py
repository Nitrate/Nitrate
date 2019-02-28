# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-18 15:22
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('testcases', '0006_unique_case_component'),
    ]

    operations = [
        migrations.AlterField(
            model_name='testcase',
            name='default_tester',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cases_as_default_tester', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='testcase',
            name='reviewer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cases_as_reviewer', to=settings.AUTH_USER_MODEL),
        ),
    ]
