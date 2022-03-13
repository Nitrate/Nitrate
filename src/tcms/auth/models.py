# -*- coding: utf-8 -*-

import datetime
import secrets
from hashlib import sha256

from django.db import models


class UserActivateKey(models.Model):
    activation_key = models.CharField(max_length=64, null=True, blank=True)
    key_expires = models.DateTimeField(null=True, blank=True)

    user = models.ForeignKey("auth.User", on_delete=models.CASCADE)

    class Meta:
        db_table = "tcms_user_activate_keys"

    @classmethod
    def set_random_key_for_user(cls, user, force=False) -> "UserActivateKey":
        # How many bytes is proper to generate the salt?
        salt = secrets.token_bytes(16)
        activation_key = sha256(salt + user.username.encode("utf-8")).hexdigest()

        # Create and save their profile
        k, c = cls.objects.get_or_create(user=user)
        if c or force:
            k.activation_key = activation_key
            k.key_expires = datetime.datetime.today() + datetime.timedelta(7)
            k.save()

        return k
