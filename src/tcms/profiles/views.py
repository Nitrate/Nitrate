# -*- coding: utf-8 -*-

from django import http
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_http_methods

from tcms.profiles.forms import UserProfileForm
from tcms.profiles.models import UserProfile
from tcms.testplans.models import TestPlan
from tcms.testruns.data import stats_case_runs_status
from tcms.testruns.models import TestRun

MODULE_NAME = "profile"


@require_http_methods(["GET", "POST"])
@login_required
@csrf_protect
def profile(request, username, template_name="profile/info.html"):
    """Edit the profiles of the user"""
    u = get_object_or_404(User, username=username)

    try:
        up = UserProfile.get_user_profile(u)
    except ObjectDoesNotExist:
        up = UserProfile.objects.create(user=u)
    message = None
    form = UserProfileForm(instance=up)
    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=up)
        if form.is_valid():
            form.save()
            message = "Information successfully updated."
    context_data = {
        "user_profile": up,
        "form": form,
        "message": message,
    }
    return render(request, template_name, context=context_data)


@require_GET
@login_required
def recent(request, username):
    """List the recent plan/run"""

    if username != request.user.username:
        return http.HttpResponseRedirect(reverse("nitrate-login"))

    plans_subtotal = {
        item["is_active"]: item["count"]
        for item in TestPlan.objects.values("is_active").annotate(count=Count("pk"))
    }
    plans_count = sum(plans_subtotal.values())
    disabled_plans_count = plans_subtotal.get(False, 0)

    plans = (
        TestPlan.objects.filter(Q(author=request.user) | Q(owner=request.user), is_active=True)
        .select_related("product", "type")
        .order_by("-plan_id")
        .only("name", "is_active", "type__name", "product__name")
    )

    plans = TestPlan.apply_subtotal(plans, runs_count=True)

    runs = (
        TestRun.list({"people": request.user, "is_active": True, "status": "running"})
        .only("summary", "start_date")
        .order_by("-run_id")
    )

    first_15_runs = runs[:15]

    subtotal = stats_case_runs_status([item.pk for item in first_15_runs])
    for run in first_15_runs:
        run.case_runs_subtotal = subtotal[run.pk]

    return render(
        request,
        "profile/recent.html",
        context={
            "module": MODULE_NAME,
            "user_profile": {"user": request.user},
            "test_plans_count": plans_count,
            "test_plans_disable_count": disabled_plans_count,
            "test_runs_count": runs.count(),
            "last_15_test_plans": plans[:15],
            "last_15_test_runs": first_15_runs,
        },
    )


@login_required
def redirect_to_profile(request):
    return http.HttpResponseRedirect(reverse("user-recent", args=[request.user.username]))
