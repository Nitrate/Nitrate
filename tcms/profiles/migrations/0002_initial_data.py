# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def initial_data(apps, schema_editor):
    data = [
        {u'fields': {u'description': u'Can tweak operating parameters.',
                     u'isactive': True,
                     u'isbuggroup': 0,
                     u'name': u'tweakparams',
                     u'userregexp': u''},
         u'model': u'profiles.groups',
         u'pk': 1},
        {u'fields': {u'description': u'Can edit or disable users.',
                     u'isactive': True,
                     u'isbuggroup': 0,
                     u'name': u'editusers',
                     u'userregexp': u''},
            u'model': u'profiles.groups',
            u'pk': 2},
        {u'fields': {u'description': u'Can create and destroy groups.',
                     u'isactive': True,
                     u'isbuggroup': 0,
                     u'name': u'creategroups',
                     u'userregexp': u''},
            u'model': u'profiles.groups',
            u'pk': 3},
        {u'fields': {u'description': u'Can create, destroy, and edit classifications.',
                     u'isactive': True,
                     u'isbuggroup': 0,
                     u'name': u'editclassifications',
                     u'userregexp': u''},
            u'model': u'profiles.groups',
            u'pk': 4},
        {u'fields': {u'description': u'Can create, destroy, and edit components.',
                     u'isactive': True,
                     u'isbuggroup': 0,
                     u'name': u'editcomponents',
                     u'userregexp': u''},
            u'model': u'profiles.groups',
            u'pk': 5},
        {u'fields': {u'description': u'Can create, destroy, and edit keywords.',
                     u'isactive': True,
                     u'isbuggroup': 0,
                     u'name': u'editkeywords',
                     u'userregexp': u''},
            u'model': u'profiles.groups',
            u'pk': 6},
        {u'fields': {u'description': u'Administrators',
                     u'isactive': True,
                     u'isbuggroup': 0,
                     u'name': u'admin',
                     u'userregexp': u''},
            u'model': u'profiles.groups',
            u'pk': 7},
        {u'fields': {u'description': u'Can edit all bug fields.',
                     u'isactive': True,
                     u'isbuggroup': 0,
                     u'name': u'editbugs',
                     u'userregexp': u'.*'},
            u'model': u'profiles.groups',
            u'pk': 8},
        {u'fields': {u'description': u'Can confirm a bug.',
                     u'isactive': True,
                     u'isbuggroup': 0,
                     u'name': u'canconfirm',
                     u'userregexp': u'.*'},
            u'model': u'profiles.groups',
            u'pk': 9},
        {u'fields': {u'description': u'User can configure whine reports for self.',
                     u'isactive': True,
                     u'isbuggroup': 0,
                     u'name': u'bz_canusewhines',
                     u'userregexp': u''},
            u'model': u'profiles.groups',
            u'pk': 10},
        {u'fields': {u'description': u'Can configure whine reports for other users.',
                     u'isactive': True,
                     u'isbuggroup': 0,
                     u'name': u'bz_canusewhineatothers',
                     u'userregexp': u''},
            u'model': u'profiles.groups',
            u'pk': 11},
        {u'fields': {u'description': u'Can perform actions as other users.',
                     u'isactive': True,
                     u'isbuggroup': 0,
                     u'name': u'bz_sudoers',
                     u'userregexp': u''},
            u'model': u'profiles.groups',
            u'pk': 12},
        {u'fields': {u'description': u'Can not be impersonated by other users.',
                     u'isactive': True,
                     u'isbuggroup': 0,
                     u'name': u'bz_sudo_protect',
                     u'userregexp': u''},
            u'model': u'profiles.groups',
            u'pk': 13},
        {u'fields': {u'description': u'test group.',
                     u'isactive': True,
                     u'isbuggroup': 1,
                     u'name': u'beatles',
                     u'userregexp': u'.*'},
            u'model': u'profiles.groups',
            u'pk': 14},
        {u'fields': {u'description': u'Can read, write, and delete all test plans, runs, and cases.',
                     u'isactive': True,
                     u'isbuggroup': 0,
                     u'name': u'Testers',
                     u'userregexp': u''},
            u'model': u'profiles.groups',
            u'pk': 15}
    ]

    for record in data:
        app_name, model_name = record['model'].split('.')
        ModelClass = apps.get_model(app_name, model_name)
        R = ModelClass(**record['fields'])
        R.pk = record['pk']
        R.save()


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0001_initial')
    ]

    operations = [
        migrations.RunPython(initial_data),
    ]
