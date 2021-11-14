# -*- coding: utf-8 -*-

from operator import methodcaller

from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from kobo.django.xmlrpc.decorators import user_passes_test

from tcms.xmlrpc.decorators import log_call
from tcms.xmlrpc.serializer import XMLRPCSerializer
from tcms.xmlrpc.utils import parse_bool_value

__all__ = ("filter", "get", "get_me", "update", "join")

__xmlrpc_namespace__ = "User"


def get_user_dict(user):
    u = XMLRPCSerializer(model=user)
    u = u.serialize_model()
    if "password" in u:
        del u["password"]
    return u


@log_call(namespace=__xmlrpc_namespace__)
def filter(request, query):
    """Performs a search and returns the resulting list of test cases

    :param dict query: a mapping containing these criteria.

        * id: (int): ID
        * username: (str): User name
        * first_name: (str): User first name
        * last_name: (str): User last name
        * email: (str) Email
        * is_active: bool: Return the active users
        * groups: ForeignKey: AuthGroup

    :return: a list of mappings of found :class:`User <django.contrib.auth.models.User>`.
    :rtype: list[dict]

    Example::

        User.filter({'username__startswith': 'z'})
    """
    if "is_active" in query:
        query["is_active"] = parse_bool_value(query["is_active"])
    users = User.objects.filter(**query)
    return [get_user_dict(u) for u in users]


@log_call(namespace=__xmlrpc_namespace__)
def get(request, id):
    """Used to load an existing test case from the database.

    :param int id: user ID.
    :return: a mapping of found :class:`User <django.contrib.auth.models.User>`.
    :rtype: dict

    Example::

        User.get(2)
    """
    return get_user_dict(User.objects.get(pk=id))


@log_call(namespace=__xmlrpc_namespace__)
def get_me(request):
    """Get the information of myself.

    :return: a mapping of found :class:`User <django.contrib.auth.models.User>`.
    :rtype: dict

    Example::

        User.get_me()
    """
    return get_user_dict(request.user)


@log_call(namespace=__xmlrpc_namespace__)
def update(request, values=None, id=None):
    """
    Updates the fields of the selected user. it also can change the
    informations of other people if you have permission.

    :param int id: optional user ID. Defaults to update current user if
        omitted.
    :param dict values: a mapping containing these data to update a user.

        * first_name: (str) optional
        * last_name: (str) optional (**Required** if changes category)
        * email: (str) optional
        * password: (str) optional
        * old_password: (str) **Required** by password

    :return: a mapping representing the updated user.
    :rtype: dict

    Example::

        User.update({'first_name': 'foo'})
        User.update({'password': 'foo', 'old_password': '123'})
        User.update({'password': 'foo', 'old_password': '123'}, 2)
    """
    if id:
        user_being_updated = User.objects.get(pk=id)
    else:
        user_being_updated = request.user

    if values is None:
        values = {}

    editable_fields = ("first_name", "last_name", "email", "password")
    can_change_user = request.user.has_perm("auth.change_user")

    is_updating_other = request.user != user_being_updated
    # If change other's attributes, current user must have proper permission
    # Otherwise, to allow to update my own attribute without specific
    # permission assignment
    if not can_change_user and is_updating_other:
        raise PermissionDenied("Permission denied")

    update_fields = []
    for field in editable_fields:
        if not values.get(field):
            continue

        update_fields.append(field)
        if field == "password":
            # FIXME: here, permission control has bug, that cause changing
            # password is not controlled under permission.
            old_password = values.get("old_password")
            if not can_change_user and not old_password:
                raise PermissionDenied("Old password is required")

            if not can_change_user and not user_being_updated.check_password(old_password):
                raise PermissionDenied("Password is incorrect")

            user_being_updated.set_password(values["password"])
        else:
            setattr(user_being_updated, field, values[field])

    user_being_updated.save(update_fields=update_fields)
    return get_user_dict(user_being_updated)


@log_call(namespace=__xmlrpc_namespace__)
@user_passes_test(methodcaller("has_perm", "auth.change_user"))
def join(request, username, groupname):
    """Add user to a group specified by name.

    :param str username: user name.
    :param str groupname: group name to add given user name.

    :raise PermissionDenied: if the request has no permission to add a user to
        a group.
    :raise Object.DoesNotExist: if user name or group name does not exist.

    Example::

        User.join('username', 'groupname')
    """
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        raise User.DoesNotExist('User "%s" does not exist' % username)
    else:
        try:
            group = Group.objects.get(name=groupname)
        except Group.DoesNotExist:
            raise Group.DoesNotExist('Group "%s" does not exist' % groupname)
        else:
            user.groups.add(group)
