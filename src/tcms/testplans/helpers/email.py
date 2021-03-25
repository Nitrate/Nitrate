# -*- coding: utf-8 -*-

from tcms.core.mailto import mail_notify


def email_plan_update(plan):
    mail_notify(
        plan,
        "mail/change_plan.txt",
        f"TestPlan {plan.pk} has been updated.",
        {
            "plan_name": plan.name,
            "full_url": plan.get_full_url(),
            "updated_by": plan.current_user.username,
        },
    )


def email_plan_deletion(plan):
    mail_notify(
        plan,
        "mail/delete_plan.txt",
        f"TestPlan {plan.pk} has been deleted.",
        {"plan_name": plan.name},
    )
