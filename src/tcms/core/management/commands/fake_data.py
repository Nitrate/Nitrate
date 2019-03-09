# -*- coding: utf-8 -*-

from django.contrib.auth.models import User

from tcms.management import models as mgt_models
from tcms.testplans import models as plans_models
from tcms.profiles import models as profile_models

user = User.objects.get(username='admin')


#webapp = mgt_models.Classification.objects.create(
    #name='WebApp',
    #description='Web Application')

#product = mgt_models.Product.objects.create(
    #name='Nitrate',
    #classification=webapp,
    #description='Nitrate Demo app')

#plan_1 = plans_models.TestPlan.objects.create(
    #name='Test plan 1',
#)

bookmarks = (
    ('name', 'http://localhost/bookmark/')
)

for i in range(55):
    profile_models.Bookmark.objects.create(
        user=user,
        name=f'name {i}',
        url=f'http://localhost/bookmark/{i}',
        description=f'Bookmark for name {i}')
