# -*- coding: utf-8 -*-
# FIXME: Use signal to handle log

from tcms.core.mailto import mail_notify


def mail_notify_on_test_run_creation_or_update(sender, **kwargs):
    run = kwargs["instance"]
    if kwargs.get("created"):
        template = "mail/new_run.txt"
        subject = f"A new test run is created from plan {run.plan.pk}: {run.summary}"
    else:
        template = "mail/update_run.txt"
        subject = f"Test Run {run.pk} - {run.summary} has been updated"
    context = {
        "run_id": run.pk,
        "full_url": run.get_full_url(),
        "build": run.build.name,
        "default_tester": run.default_tester.username,
        "estimated_time": run.estimated_time,
        "manager": run.manager.username,
        "notes": run.notes,
        "plan_name": run.plan.name,
        "product": run.build.product.name,
        "product_version": run.product_version.value,
        "summary": run.summary,
    }
    mail_notify(run, template, subject, context)


def post_case_run_saved(sender, *args, **kwargs):
    instance = kwargs["instance"]
    if kwargs.get("created"):
        tr = instance.run
        tr.update_completion_status(is_auto_updated=True)


def post_case_run_deleted(sender, **kwargs):
    instance = kwargs["instance"]
    tr = instance.run
    tr.update_completion_status(is_auto_updated=True)


def post_update_handler(sender, **kwargs):
    instances = kwargs["instances"]
    instance = instances[0]
    tr = instance.run
    tr.update_completion_status(is_auto_updated=True)


def pre_save_clean(sender, **kwargs):
    instance = kwargs["instance"]
    instance.clean()


# new testrun created info for qpid
def qpid_run_created(sender, *args, **kwargs):
    # TODO: Send message to message bus when test run is created.
    # Topic: testrun.created
    pass
