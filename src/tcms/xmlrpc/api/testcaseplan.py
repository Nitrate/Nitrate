# -*- coding: utf-8 -*-

from tcms.testcases.models import TestCase, TestCasePlan
from tcms.testplans.models import TestPlan
from tcms.xmlrpc.decorators import log_call
from tcms.xmlrpc.serializer import XMLRPCSerializer

__all__ = ("get", "update")

__xmlrpc_namespace__ = "TestCasePlan"


@log_call(namespace=__xmlrpc_namespace__)
def get(request, case_id, plan_id):
    """Used to load an existing test-case-plan from the database.

    :param int case_id: case ID.
    :param int plan_id: plan ID.
    :return: a mapping of :class:`TestCasePlan`.
    :rtype: dict

    Example::

        TestCasePlan.get(1, 2)
    """
    tc = TestCase.objects.get(pk=case_id)
    tp = TestPlan.objects.get(pk=plan_id)
    tcp = TestCasePlan.objects.get(plan=tp, case=tc)
    return XMLRPCSerializer(model=tcp).serialize_model()


@log_call(namespace=__xmlrpc_namespace__)
def update(request, case_id, plan_id, sortkey):
    """Updates the sortkey of the selected test-case-plan.

    :param int case_id: case ID.
    :param int plan_id: plan ID.
    :param int sortkey: the sort key.
    :return: a mapping of :class:`TestCasePlan`.
    :rtype: dict

    Example::

        # Update sortkey of selected test-case-plan to 10
        TestCasePlan.update(1, 2, 10)
    """
    tc = TestCase.objects.get(pk=case_id)
    tp = TestPlan.objects.get(pk=plan_id)
    tcp = TestCasePlan.objects.get(plan=tp, case=tc)

    if isinstance(sortkey, int):
        tcp.sortkey = sortkey
        tcp.save(update_fields=["sortkey"])

    return XMLRPCSerializer(model=tcp).serialize_model()
