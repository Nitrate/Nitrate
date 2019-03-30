# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError

from tcms.management import models as mgt_models
from tcms.testplans import models as plans_models
from tcms.profiles import models as profile_models


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


def create_fake_data():
    user = User.objects.get(username='admin')
    site = Site.objects.get_current()

    bookmarks = (
        ('name', 'http://localhost/bookmark/')
    )

    for i in range(55):
        profile_models.Bookmark.objects.create(
            user=user,
            name=f'name {i}',
            url=f'http://localhost/bookmark/{i}',
            description=f'Bookmark for name {i}',
            site=site)

    classification, _ = mgt_models.Classification.objects.get_or_create(name='WebApp')
    product, _ = mgt_models.Product.objects.get_or_create(
        name='TestProduct', classification=classification)
    version_1_0, _ = mgt_models.Version.objects.get_or_create(product=product, value='1.0')
    version_2_0, _ = mgt_models.Version.objects.get_or_create(product=product, value='2.0')
    plan_type, _ = plans_models.TestPlanType.objects.get_or_create(name='Function')

    for i in range(100):
        if plans_models.TestPlan.objects.filter(pk=i + 1).exists():
            continue
        plans_models.TestPlan.objects.create(
            name='Test Plan {}'.format(i + 1),
            product=product,
            product_version=version_1_0,
            type=plan_type,
            author=user)


class Command(BaseCommand):
    help = (
        'Create fake data only for running Nitrate locally for development purpose.'
    )

    def handle(self, *args, **options):
        create_fake_data()
