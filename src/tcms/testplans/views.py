# -*- coding: utf-8 -*-

import datetime
import functools
import itertools
import json
import urllib
from operator import add, itemgetter
from typing import List, Optional, Set

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponsePermanentRedirect,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, render
from django.template.loader import get_template
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.views.generic import View
from django.views.generic.base import TemplateView
from uuslug import slugify

from tcms.core.db import SQLExecution
from tcms.core.models import TCMSLog
from tcms.core.responses import JsonResponseBadRequest, JsonResponseNotFound
from tcms.core.utils import DataTableResult, checksum
from tcms.core.views import prompt
from tcms.management.models import Component, TCMSEnvGroup
from tcms.testcases.data import get_exported_cases_and_related_data
from tcms.testcases.forms import QuickSearchCaseForm, SearchCaseForm
from tcms.testcases.models import TestCase, TestCasePlan, TestCaseStatus
from tcms.testcases.views import get_selected_testcases
from tcms.testplans import sqls
from tcms.testplans.forms import (
    ClonePlanForm,
    EditPlanForm,
    ImportCasesViaXMLForm,
    NewPlanForm,
    PlanComponentForm,
    SearchPlanForm,
)
from tcms.testplans.models import TestPlan, TestPlanComponent
from tcms.testruns.models import TestCaseRun, TestRun

MODULE_NAME = "testplans"

# _____________________________________________________________________________
# helper functons


def update_plan_email_settings(tp, form):
    """Update testplan's email settings"""
    tp.email_settings.notify_on_plan_update = form.cleaned_data["notify_on_plan_update"]
    tp.email_settings.notify_on_plan_delete = form.cleaned_data["notify_on_plan_delete"]
    tp.email_settings.notify_on_case_update = form.cleaned_data["notify_on_case_update"]
    tp.email_settings.auto_to_plan_owner = form.cleaned_data["auto_to_plan_owner"]
    tp.email_settings.auto_to_plan_author = form.cleaned_data["auto_to_plan_author"]
    tp.email_settings.auto_to_case_owner = form.cleaned_data["auto_to_case_owner"]
    tp.email_settings.auto_to_case_default_tester = form.cleaned_data["auto_to_case_default_tester"]
    tp.email_settings.save()


# _____________________________________________________________________________
# view functions


class CreateNewPlanView(PermissionRequiredMixin, View):
    """Create a new test plan view"""

    sub_module_name = "new_plan"
    template_name = "plan/new.html"
    permission_required = (
        "testplans.add_testplan",
        "testplans.add_testplantext",
        "testplans.add_tcmsenvplanmap",
    )

    def make_response(self, form):
        return render(
            self.request,
            self.template_name,
            context={
                "module": MODULE_NAME,
                "sub_module": self.sub_module_name,
                "form": form,
            },
        )

    def get(self, request):
        return self.make_response(NewPlanForm())

    @method_decorator(csrf_protect)
    def post(self, request):
        form = NewPlanForm(request.POST, request.FILES)
        form.populate(product_id=request.POST.get("product"))

        if not form.is_valid():
            return self.make_response(form)

        # Process the upload plan document
        if form.cleaned_data.get("upload_plan_text"):
            # A document is uploaded to provide the document content. Load the
            # page again in order to show the content.
            initial_data = {
                "name": form.cleaned_data["name"],
                "type": form.cleaned_data["type"].pk,
                "product": form.cleaned_data["product"].pk,
                "product_version": form.cleaned_data["product_version"].pk,
                "extra_link": form.cleaned_data["extra_link"],
                "text": form.cleaned_data["text"],
            }
            if form.cleaned_data["env_group"]:
                initial_data["env_group"] = form.cleaned_data["env_group"].pk
            return self.make_response(NewPlanForm(initial=initial_data))

        # Process the test plan submit to the form
        tp = TestPlan.objects.create(
            product=form.cleaned_data["product"],
            author=request.user,
            owner=request.user,
            product_version=form.cleaned_data["product_version"],
            type=form.cleaned_data["type"],
            name=form.cleaned_data["name"],
            create_date=datetime.datetime.now(),
            extra_link=form.cleaned_data["extra_link"],
            parent=form.cleaned_data["parent"],
        )

        tp.add_text(author=request.user, plan_text=form.cleaned_data["text"])

        # Add test plan environment groups
        if request.POST.get("env_group"):
            env_groups = TCMSEnvGroup.objects.filter(id__in=request.POST.getlist("env_group"))

            for env_group in env_groups:
                tp.add_env_group(env_group=env_group)

        return HttpResponseRedirect(reverse("plan-get", args=[tp.plan_id]))


@require_GET
@permission_required("testplans.delete_testplan")
def delete(request, plan_id):
    """Delete testplan"""
    if request.GET.get("sure", "no") == "no":
        # TODO: rewrite the response
        plan_delete_url = reverse("plan-delete", args=[plan_id])
        return HttpResponse(
            "<script>"
            "if (confirm('Are you sure you want to delete this plan %s?\\n\\n"
            "Click OK to delete or cancel to come back'))"
            "{ window.location.href='%s?sure=yes' }"
            "else { history.go(-1) }"
            "</script>" % (plan_id, plan_delete_url)
        )
    elif request.GET.get("sure") == "yes":
        tp = get_object_or_404(TestPlan, plan_id=plan_id)

        try:
            tp.delete()
            return HttpResponse(
                "<script>window.location.href='%s'</script>" % reverse("tcms.testplans.views.all")
            )
        except Exception:
            return prompt.info(request, "Delete failed.")
    else:
        return prompt.info(request, "Nothing yet.")


class SimplePlansFilterView(TemplateView):
    """Providing base plans filter functionaity"""

    # Subclass should provide a concrete template to render the final content.
    # Or, pass the template path to argument template_name of View.as_view()
    template_name = None

    def filter_plans(self):
        search_form = SearchPlanForm(self.request.GET)
        product_id = self.request.GET.get("product")
        search_form.populate(int(product_id) if product_id else None)

        plans = TestPlan.objects.none()

        if search_form.is_valid():
            # Determine the query is the user's plans and change the sub module value
            author = self.request.GET.get("author__email__startswith")
            req_user = self.request.user
            if req_user.is_authenticated and author in (
                req_user.username,
                req_user.email,
            ):
                self.SUB_MODULE_NAME = "my_plans"

            plans = (
                TestPlan.list(search_form.cleaned_data)
                .select_related("author", "type", "product")
                .order_by("-create_date")
            )

            plans = TestPlan.apply_subtotal(
                plans,
                cases_count=True,
                runs_count=True,
                children_count=True,
            )

        return search_form, plans

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_plan_form"], context["plans"] = self.filter_plans()
        return context


class SearchPlansView(SimplePlansFilterView):
    """Used to filter test plans"""

    SUB_MODULE_NAME = "plans"
    template_name = "plan/all.html"

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "module": MODULE_NAME,
                "sub_module": self.SUB_MODULE_NAME,
                "object_list": context["plans"][0:20],
                "plans_count": context["plans"].count(),
            }
        )
        return context


class SearchPlansPagesView(SimplePlansFilterView):

    template_name = "plan/common/json_plans.txt"
    column_names = [
        "",
        "plan_id",
        "name",
        "author__username",
        "owner__username",
        "product",
        "product_version",
        "type",
        "cases_count",
        "runs_count",
        "",
    ]

    def get(self, request, *args, **kwargs):
        _, plans = self.filter_plans()
        dt = DataTableResult(request.GET, plans, self.column_names)
        data = dt.get_response_data()
        resp_data = get_template(self.template_name).render(data, request)
        return JsonResponse(json.loads(resp_data))


def get(request, plan_id, slug=None, template_name="plan/get.html"):
    """Display the plan details."""
    SUB_MODULE_NAME = "plans"

    try:
        tp = TestPlan.objects.select_related().get(plan_id=plan_id)
        tp.latest_text = tp.latest_text()
    except ObjectDoesNotExist:
        raise Http404

    # redirect if has a cheated slug
    if slug != slugify(tp.name):
        return HttpResponsePermanentRedirect(tp.get_absolute_url())

    # Initial the case counter
    confirm_status_name = "CONFIRMED"
    tp.run_case = tp.case.filter(case_status__name=confirm_status_name)
    tp.review_case = tp.case.exclude(case_status__name=confirm_status_name)

    context_data = {
        "module": MODULE_NAME,
        "sub_module": SUB_MODULE_NAME,
        "test_plan": tp,
        "xml_form": ImportCasesViaXMLForm(),
    }
    return render(request, template_name, context=context_data)


class AddCasesToRunsView(PermissionRequiredMixin, View):
    """View of adding cases to runs"""

    SUB_MODULE_NAME = "runs"
    permission_required = "testruns.change_testrun"
    template_name = "plan/choose_testrun.html"

    def get(self, request, plan_id):
        plan = TestPlan.objects.filter(pk=int(plan_id)).defer("product_version").first()
        if plan is None:
            raise Http404

        # TODO: replace with plan.run.values(...)
        runs = TestRun.objects.filter(plan=plan_id).values(
            "pk", "summary", "build__name", "manager__username"
        )

        cases = get_selected_testcases(request).values(
            "pk",
            "summary",
            "author__username",
            "create_date",
            "category__name",
            "priority__value",
        )

        return render(
            request,
            self.template_name,
            context={
                "module": MODULE_NAME,
                "sub_module": self.SUB_MODULE_NAME,
                "plan_id": plan_id,
                "plan": plan,
                "test_runs": runs.iterator(),
                "test_cases": cases,
            },
        )

    def post(self, request, plan_id):
        choosed_testrun_ids = request.POST.getlist("testrun_ids")
        to_be_added_cases = TestCase.objects.filter(pk__in=request.POST.getlist("case_ids"))

        plan_url = reverse("plan-get", args=[plan_id])

        # cases and runs are required in this process
        if not len(choosed_testrun_ids) or not len(to_be_added_cases):
            return prompt.info(
                request,
                "At least one test run and one case is required to add cases to runs.",
                plan_url,
            )

        # Adding cases to runs by recursion
        for tr_id in choosed_testrun_ids:
            testrun = get_object_or_404(TestRun, run_id=tr_id)
            cases = TestCaseRun.objects.filter(run=tr_id)
            exist_cases_id = cases.values_list("case", flat=True)

            for testcase in to_be_added_cases:
                if testcase.case_id not in exist_cases_id:
                    testrun.add_case_run(case=testcase)

            estimated_time = functools.reduce(add, [nc.estimated_time for nc in to_be_added_cases])
            testrun.estimated_time = testrun.estimated_time + estimated_time
            testrun.save()

        return HttpResponseRedirect(plan_url)


@require_http_methods(["GET", "POST"])
@permission_required("testplans.change_testplan")
def edit(request, plan_id, template_name="plan/edit.html"):
    """Edit test plan view"""
    # Define the default sub module
    SUB_MODULE_NAME = "plans"

    try:
        tp = TestPlan.objects.select_related().get(plan_id=plan_id)
    except ObjectDoesNotExist:
        raise Http404

    # If the form is submitted
    if request.method == "POST":
        form = EditPlanForm(request.POST, request.FILES)
        if request.POST.get("product"):
            form.populate(product_id=request.POST["product"])
        else:
            form.populate()

        # FIXME: Error handle
        if form.is_valid():
            if form.cleaned_data.get("upload_plan_text"):
                # Set the summary form field to the uploaded text
                form.data["text"] = form.cleaned_data["text"]

                # Generate the form
                context_data = {
                    "module": MODULE_NAME,
                    "sub_module": SUB_MODULE_NAME,
                    "form": form,
                    "test_plan": tp,
                }
                return render(request, template_name, context=context_data)

            if request.user.has_perm("testplans.change_testplan"):
                tp.name = form.cleaned_data["name"]
                tp.parent = form.cleaned_data["parent"]
                tp.product = form.cleaned_data["product"]
                tp.product_version = form.cleaned_data["product_version"]
                tp.type = form.cleaned_data["type"]
                tp.is_active = form.cleaned_data["is_active"]
                tp.extra_link = form.cleaned_data["extra_link"]
                tp.owner = form.cleaned_data["owner"]
                # IMPORTANT! tp.current_user is an instance attribute,
                # added so that in post_save, current logged-in user info
                # can be accessed.
                # Instance attribute is usually not a desirable solution.
                tp.current_user = request.user
                tp.save()

            if request.user.has_perm("testplans.add_testplantext"):
                new_text = request.POST.get("text")
                text_checksum = checksum(new_text)

                if not tp.text_exist() or text_checksum != tp.text_checksum():
                    tp.add_text(
                        author=request.user,
                        plan_text=request.POST.get("text"),
                        text_checksum=text_checksum,
                    )

            if request.user.has_perm("management.change_tcmsenvplanmap"):
                tp.clear_env_groups()

                if request.POST.get("env_group"):
                    env_groups = TCMSEnvGroup.objects.filter(
                        id__in=request.POST.getlist("env_group")
                    )

                    for env_group in env_groups:
                        tp.add_env_group(env_group=env_group)
            # Update plan email settings
            update_plan_email_settings(tp, form)
            return HttpResponseRedirect(reverse("plan-get", args=[plan_id, slugify(tp.name)]))
    else:
        # Generate a blank form
        # Temporary use one environment group in this case
        if tp.env_group.all():
            for env_group in tp.env_group.all():
                env_group_id = env_group.id
                break
        else:
            env_group_id = None

        form = EditPlanForm(
            initial={
                "name": tp.name,
                "product": tp.product_id,
                "product_version": tp.product_version_id,
                "type": tp.type_id,
                "text": tp.latest_text() and tp.latest_text().plan_text or "",
                "parent": tp.parent_id,
                "env_group": env_group_id,
                "is_active": tp.is_active,
                "extra_link": tp.extra_link,
                "owner": tp.owner,
                "auto_to_plan_owner": tp.email_settings.auto_to_plan_owner,
                "auto_to_plan_author": tp.email_settings.auto_to_plan_author,
                "auto_to_case_owner": tp.email_settings.auto_to_case_owner,
                "auto_to_case_default_tester": tp.email_settings.auto_to_case_default_tester,
                "notify_on_plan_update": tp.email_settings.notify_on_plan_update,
                "notify_on_case_update": tp.email_settings.notify_on_case_update,
                "notify_on_plan_delete": tp.email_settings.notify_on_plan_delete,
            }
        )
        form.populate(product_id=tp.product_id)

    context_data = {
        "module": MODULE_NAME,
        "sub_module": SUB_MODULE_NAME,
        "test_plan": tp,
        "form": form,
    }
    return render(request, template_name, context=context_data)


@require_http_methods(["GET", "POST"])
@permission_required("testplans.add_testplan")
def clone(request, template_name="plan/clone.html"):
    """Clone testplan"""
    SUB_MODULE_NAME = "plans"

    req_data = request.GET or request.POST
    if "plan" not in req_data:
        return prompt.info(
            request,
            "At least one plan is required by clone function.",
        )

    tps = TestPlan.objects.filter(pk__in=req_data.getlist("plan")).order_by("-pk")

    if not tps:
        return prompt.info(
            request,
            "The plan you specify does not exist in database.",
        )

    # Clone the plan if the form is submitted
    if request.method == "POST":
        clone_form = ClonePlanForm(request.POST)
        clone_form.populate(product_id=request.POST.get("product_id"))

        if clone_form.is_valid():
            clone_options = clone_form.cleaned_data

            # Create new test plan.
            for tp in tps:

                new_name = len(tps) == 1 and clone_options["name"] or None

                clone_params = {
                    # Cloned plan properties
                    "new_name": new_name,
                    "product": clone_options["product"],
                    "version": clone_options["product_version"],
                    "set_parent": clone_options["set_parent"],
                    # Related data
                    "copy_texts": clone_options["copy_texts"],
                    "copy_attachments": clone_options["copy_attachements"],
                    "copy_environment_group": clone_options["copy_environment_group"],
                    # Link or copy cases
                    "link_cases": clone_options["link_testcases"],
                    "copy_cases": clone_options["copy_testcases"],
                    "default_component_initial_owner": request.user,
                }

                assign_me_as_plan_author = not clone_options["keep_orignal_author"]
                if assign_me_as_plan_author:
                    clone_params["new_original_author"] = request.user

                assign_me_as_copied_case_author = (
                    clone_options["copy_testcases"]
                    and not clone_options["maintain_case_orignal_author"]
                )
                if assign_me_as_copied_case_author:
                    clone_params["new_case_author"] = request.user

                assign_me_as_copied_case_default_tester = (
                    clone_options["copy_testcases"]
                    and not clone_options["keep_case_default_tester"]
                )
                if assign_me_as_copied_case_default_tester:
                    clone_params["new_case_default_tester"] = request.user

                assign_me_as_text_author = not clone_options["copy_texts"]
                if assign_me_as_text_author:
                    clone_params["default_text_author"] = request.user

                cloned_plan = tp.clone(**clone_params)

            if len(tps) == 1:
                return HttpResponseRedirect(reverse("plan-get", args=[cloned_plan.plan_id]))
            else:
                args = {
                    "action": "search",
                    "product": clone_form.cleaned_data["product"].id,
                    "product_version": clone_form.cleaned_data["product_version"].id,
                }
                url_args = urllib.parse.urlencode(args)
                return HttpResponseRedirect("{}?{}".format(reverse("plans-all"), url_args))
    else:
        # Generate the default values for the form
        if len(tps) == 1:
            clone_form = ClonePlanForm(
                initial={
                    "product": tps[0].product_id,
                    "product_version": tps[0].product_version_id,
                    "set_parent": True,
                    "copy_texts": True,
                    "copy_attachements": True,
                    "copy_environment_group": True,
                    "link_testcases": True,
                    "copy_testcases": False,
                    "maintain_case_orignal_author": True,
                    "keep_case_default_tester": False,
                    "name": tps[0].make_cloned_name(),
                }
            )
            clone_form.populate(product_id=tps[0].product.id)
        else:
            clone_form = ClonePlanForm(
                initial={
                    "set_parent": True,
                    "copy_texts": True,
                    "copy_attachements": True,
                    "link_testcases": True,
                    "copy_testcases": False,
                    "maintain_case_orignal_author": True,
                    "keep_case_default_tester": True,
                }
            )

    context_data = {
        "module": MODULE_NAME,
        "sub_module": SUB_MODULE_NAME,
        "testplans": tps,
        "clone_form": clone_form,
    }
    return render(request, template_name, context=context_data)


def attachment(request, plan_id, template_name="plan/attachment.html"):
    """Manage attached files"""
    SUB_MODULE_NAME = "plans"

    file_size_limit = settings.MAX_UPLOAD_SIZE
    limit_readable = int(file_size_limit) / 2 ** 20  # Mb

    tp = get_object_or_404(TestPlan, plan_id=plan_id)
    context_data = {
        "module": MODULE_NAME,
        "sub_module": SUB_MODULE_NAME,
        "test_plan": tp,
        "limit": file_size_limit,
        "limit_readable": str(limit_readable) + "Mb",
    }
    return render(request, template_name, context=context_data)


@require_GET
def text_history(request, plan_id, template_name="plan/history.html"):
    """View test plan text history"""
    SUB_MODULE_NAME = "plans"

    tp = get_object_or_404(TestPlan, plan_id=int(plan_id))
    tptxts = tp.text.select_related("author").only(
        "plan", "create_date", "plan_text", "plan_text_version", "author__email"
    )
    selected_plan_text_version = int(request.GET.get("plan_text_version", 0))
    context_data = {
        "module": MODULE_NAME,
        "sub_module": SUB_MODULE_NAME,
        "testplan": tp,
        "test_plan_texts": tptxts,
        "select_plan_text_version": selected_plan_text_version,
    }
    return render(request, template_name, context=context_data)


class ReorderCasesView(View):
    """Reorder cases"""

    http_method_names = ["post"]

    def post(self, request, plan_id):
        # Current we should rewrite all of cases belong to the plan.
        # Because the cases sortkey in database is chaos,
        # Most of them are None.

        if "case" not in request.POST:
            return JsonResponseBadRequest({"message": "At least one case is required to re-order."})

        plan = get_object_or_404(TestPlan, pk=int(plan_id))

        case_ids = [int(id) for id in request.POST.getlist("case")]
        cases = TestCase.objects.filter(pk__in=case_ids).only("pk")

        for case in cases:
            new_sort_key = (case_ids.index(case.pk) + 1) * 10
            TestCasePlan.objects.filter(plan=plan, case=case).update(sortkey=new_sort_key)

        return JsonResponse({})


class LinkCasesView(View):
    """Link cases to plan"""

    permission_required = "testcases.add_testcaseplan"

    def post(self, request, plan_id):
        plan = get_object_or_404(TestPlan.objects.only("pk"), pk=int(plan_id))
        case_ids = [int(id) for id in request.POST.getlist("case")]
        cases = TestCase.objects.filter(case_id__in=case_ids).only("pk")
        for case in cases:
            plan.add_case(case)
        return HttpResponseRedirect(reverse("plan-get", args=[plan_id]))


class LinkCasesSearchView(View):
    """Search cases for linking to plan"""

    template_name = "plan/search_case.html"
    SUB_MODULE_NAME = "plans"

    def get(self, request, plan_id):
        plan = get_object_or_404(TestPlan, pk=int(plan_id))

        normal_form = SearchCaseForm(
            initial={
                "product": plan.product_id,
                "product_version": plan.product_version_id,
                "case_status_id": TestCaseStatus.get("CONFIRMED"),
            }
        )
        quick_form = QuickSearchCaseForm()
        return render(
            self.request,
            self.template_name,
            {
                "module": MODULE_NAME,
                "sub_module": self.SUB_MODULE_NAME,
                "search_form": normal_form,
                "quick_form": quick_form,
                "test_plan": plan,
            },
        )

    def post(self, request, plan_id):
        plan = get_object_or_404(TestPlan, pk=int(plan_id))

        search_mode = request.POST.get("search_mode")
        if search_mode == "quick":
            form = quick_form = QuickSearchCaseForm(request.POST)
            normal_form = SearchCaseForm()
        else:
            form = normal_form = SearchCaseForm(request.POST)
            form.populate(product_id=request.POST.get("product"))
            quick_form = QuickSearchCaseForm()

        if form.is_valid():
            cases = TestCase.list(form.cleaned_data)
            cases = (
                cases.select_related("author", "default_tester", "case_status", "priority")
                .only(
                    "pk",
                    "summary",
                    "create_date",
                    "author__email",
                    "default_tester__email",
                    "case_status__name",
                    "priority__value",
                )
                .exclude(case_id__in=plan.case.values_list("case_id", flat=True))
            )

        context = {
            "module": MODULE_NAME,
            "sub_module": self.SUB_MODULE_NAME,
            "test_plan": plan,
            "test_cases": cases,
            "search_form": normal_form,
            "quick_form": quick_form,
            "search_mode": search_mode,
        }
        return render(request, self.template_name, context=context)


class ImportCasesView(PermissionRequiredMixin, View):
    """Import cases to a plan"""

    permission_required = "testcases.add_testcaseplan"

    def post(self, request, plan_id):
        plan = get_object_or_404(TestPlan.objects.only("pk"), pk=int(plan_id))
        next_url = reverse("plan-get", args=[plan_id]) + "#testcases"
        xml_form = ImportCasesViaXMLForm(request.POST, request.FILES)
        if xml_form.is_valid():
            plan.import_cases(xml_form.cleaned_data["xml_file"])
            return HttpResponseRedirect(next_url)
        else:
            return prompt.alert(request, xml_form.errors, next_url)


class DeleteCasesView(View):
    """Delete selected cases from plan"""

    def post(self, request, plan_id):
        plan = get_object_or_404(TestPlan.objects.only("pk"), pk=int(plan_id))

        if "case" not in request.POST:
            return JsonResponseBadRequest({"message": "At least one case is required to delete."})

        cases = get_selected_testcases(request).only("pk")

        # Log Action
        plan_log = TCMSLog(model=plan)
        for case in cases:
            plan_log.make(who=request.user, new_value=f"Remove case {case.pk} from plan {plan.pk}")
            case.log_action(who=request.user, new_value=f"Remove from plan {plan.pk}")
            plan.delete_case(case=case)

        return JsonResponse({})


class PlanComponentsActionView(View):
    """Manage a plan's components"""

    template_name = "plan/get_component.html"

    def get(self, request):
        if "plan" not in request.GET:
            return HttpResponseBadRequest("Plan ID is not in request.")
        plans = TestPlan.objects.filter(pk=int(request.GET["plan"]))
        if not plans:
            return Http404("Plan ID {} does not exist.".format(", ".join(plans)))

        action = request.GET.get("a", "get_component_list").lower()

        if action == "get_form":
            return self.get_manage_form(request, plans)
        elif action == "get_component_list":
            return self.get_default_component_list(request, plans[0])
        elif action == "add":
            return self.add(request, plans[0], self._get_components())
        elif action == "remove":
            components = self._get_components()
            return self.remove_components_from_plan(request, plans[0], components)
        elif action == "update":
            return self.update_components(request, plans[0])

    def _get_components(self):
        if "component" not in self.request.GET:
            return HttpResponseBadRequest("Component ID is not in request.")
        component_ids = [int(id) for id in self.request.GET.getlist("component")]
        return Component.objects.filter(pk__in=component_ids)

    @method_decorator(permission_required("testplans.add_testplancomponent"))
    def add(self, request, plan, components):
        """Add components to given plans"""
        list(map(plan.add_component, components))

    @method_decorator(permission_required("testplans.delete_testplancomponent"))
    def remove_components_from_plan(self, request, plan, components=None):
        """Remove existing components from plans

        :param plan: instance of TestPlan, from which to remove components
            from this plan.
        :param components: instances of Component, which will be removed.
        """
        if components is None:
            TestPlanComponent.objects.filter(plan=plan).delete()
        else:
            list(map(plan.remove_component, components))

        return self.get_default_component_list(request, plan)

    def update_components(self, request, plan):
        self.remove_components_from_plan(request, plan)
        self.add(request, plan, self._get_components())
        return self.get_default_component_list(request, plan)

    def get_manage_form(self, request, plans):
        """Return form content in order to select components"""
        plan_comps = TestPlanComponent.objects.filter(plan__in=plans)

        form = PlanComponentForm(
            tps=plans,
            initial={
                "component": plan_comps.values_list("component_id", flat=True),
            },
        )

        q_format = request.GET.get("format", "p")
        html = getattr(form, "as_" + q_format)

        return HttpResponse(html())

    def get_default_component_list(self, request, plan):
        return render(request, self.template_name, context={"test_plan": plan})


@require_GET
def printable(request, template_name="plan/printable.html"):
    """Create the printable copy for plan"""
    plan_pks = request.GET.getlist("plan")

    if not plan_pks:
        return prompt.info(request, "At least one target is required.")

    tps = TestPlan.objects.filter(pk__in=plan_pks).only("pk", "name")

    def plan_generator():
        repeat = len(plan_pks)
        params_sql = ",".join(itertools.repeat("%s", repeat))
        sql = sqls.TP_PRINTABLE_CASE_TEXTS % (params_sql, params_sql)
        result_set = SQLExecution(sql, plan_pks * 2)
        group_data = itertools.groupby(result_set.rows, itemgetter("plan_id"))
        cases_dict = {key: list(values) for key, values in group_data}
        for tp in tps:
            tp.result_set = cases_dict.get(tp.plan_id, None)
            yield tp

    context_data = {
        "test_plans": plan_generator(),
    }

    return render(request, template_name, context=context_data)


@require_GET
def export(request, template_name="case/export.xml"):
    """Export the plan"""
    plan_pks = list(map(int, request.GET.getlist("plan")))

    if not plan_pks:
        return prompt.info(request, "At least one target is required.")

    context_data = {
        "cases_info": get_exported_cases_and_related_data(plan_pks),
    }

    timestamp = datetime.datetime.now()
    timestamp_str = "%02i-%02i-%02i" % (timestamp.year, timestamp.month, timestamp.day)

    response = render(request, template_name, context=context_data)
    filename = f"tcms-testcases-{timestamp_str}.xml"
    response["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@require_GET
def construct_plans_treeview(request, plan_id):
    """Construct a plan's tree view"""
    plan = get_object_or_404(TestPlan, pk=plan_id)

    tree_plan_ids = plan.get_ancestor_ids() + plan.get_descendant_ids()
    tree_plan_ids.append(plan.pk)

    plans = (
        TestPlan.objects.filter(pk__in=tree_plan_ids)
        .only("pk", "name", "parent_id")
        .order_by("parent_id", "pk")
    )

    plans = TestPlan.apply_subtotal(plans, cases_count=True, runs_count=True, children_count=True)

    return render(
        request,
        "plan/get_treeview.html",
        context={"current_plan_id": plan_id, "plans": plans},
    )


@login_required
@require_POST
def treeview_add_child_plans(request: HttpRequest, plan_id: int):
    plan = TestPlan.objects.filter(pk=plan_id).only("pk").first()
    if plan is None:
        return JsonResponseNotFound({"message": f"Plan {plan_id} does not exist."})

    child_plan_ids: List[str] = request.POST.getlist("children")
    child_plans: List[TestPlan] = []

    ancestor_ids = plan.get_ancestor_ids()
    descendant_ids = plan.get_descendant_ids()

    for child_plan_id in child_plan_ids:
        if not child_plan_id.isdigit():
            return JsonResponseBadRequest(
                {"message": f"Child plan id {child_plan_id} is not a number."}
            )
        child_plan: TestPlan = TestPlan.objects.filter(pk=int(child_plan_id)).only("pk").first()
        if child_plan is None:
            return JsonResponseBadRequest(
                {"message": f"Child plan {child_plan_id} does not exist."}
            )
        if child_plan.pk in ancestor_ids:
            return JsonResponseBadRequest(
                {"message": f"Plan {child_plan_id} is an ancestor of " f"plan {plan_id} already."}
            )
        if child_plan.pk in descendant_ids:
            return JsonResponseBadRequest(
                {"message": f"Plan {child_plan_id} is a descendant of " f"plan {plan_id} already."}
            )

        child_plans.append(child_plan)

    for child_plan in child_plans:
        child_plan.parent = plan
        child_plan.save(update_fields=["parent"])

    return JsonResponse(
        {"parent_plan": plan.pk, "children_plans": [plan.pk for plan in child_plans]}
    )


@login_required
@require_POST
def treeview_remove_child_plans(request, plan_id: int):
    plan: TestPlan = TestPlan.objects.filter(pk=plan_id).only("pk").first()
    if plan is None:
        return JsonResponseNotFound({"message": f"Plan {plan_id} does not exist."})

    child_plan_ids: Set[int] = set(map(int, request.POST.getlist("children")))
    direct_descendants = set(plan.get_descendant_ids(True))
    ids_to_remove = child_plan_ids & direct_descendants

    if ids_to_remove:
        TestPlan.objects.filter(pk__in=ids_to_remove).update(parent=None)

    return JsonResponse(
        {
            "parent_plan": plan.pk,
            "removed": sorted(ids_to_remove),
            "non_descendants": sorted(child_plan_ids - direct_descendants),
        }
    )


class PlanTreeChangeParentView(PermissionRequiredMixin, View):
    """Plan tree view to change a plan's parent"""

    permission_required = "testplans.change_testplan"

    def handle_no_permission(self):
        return JsonResponseBadRequest(
            {"message": "You do not have permission to change the parent plan."}
        )

    def patch(self, request, *args, **kwargs):
        plan: TestPlan = TestPlan.objects.filter(pk=self.kwargs["plan_id"]).only("pk").first()
        if plan is None:
            return JsonResponseNotFound(
                {
                    "message": f"Cannot change parent of plan, "
                    f"whose id {self.kwargs['plan_id']} does not exist."
                }
            )

        data = json.loads(request.body)
        user_input: Optional[str] = data.get("parent")
        if user_input is None:
            return JsonResponseBadRequest({"message": "Missing parent plan id."})
        if not isinstance(user_input, int):
            return JsonResponseBadRequest(
                {"message": f'The given parent plan id "{user_input}" is not a positive integer.'}
            )
        parent_id = int(user_input)
        new_parent = TestPlan.objects.filter(pk=parent_id).only("parent").first()
        if new_parent is None:
            return JsonResponseBadRequest(
                {"message": f"The parent plan id {parent_id} does not exist."}
            )

        descendant_ids = plan.get_descendant_ids()
        if parent_id in descendant_ids:
            return JsonResponseBadRequest(
                {
                    "message": f"The parent plan {parent_id} is a descendant of plan {plan.pk} already."
                }
            )

        original_value = plan.parent.pk if plan.parent else "None"

        plan.parent = new_parent
        plan.save(update_fields=["parent"])
        plan.log_action(
            who=request.user,
            field="parent",
            original_value=original_value,
            new_value=str(new_parent.pk),
        )

        return JsonResponse({})


class SetPlanActiveView(PermissionRequiredMixin, View):
    """Set a test plan active or inactive"""

    permission_required = "testplans.change_testplan"
    raise_exception = True
    enable: bool = True

    def patch(self, request, *args, **kwargs):
        plan_id = self.kwargs["plan_id"]
        plan: TestPlan = TestPlan.objects.filter(pk=plan_id).only("is_active").first()
        if not plan:
            return JsonResponseNotFound({"message": f"Plan id {plan_id} does not exist."})
        original_value: str = str(plan.is_active)
        plan.is_active = self.enable
        plan.save(update_fields=["is_active"])
        plan.log_action(
            who=request.user,
            field="is_active",
            original_value=original_value,
            new_value=str(plan.is_active),
        )
        return JsonResponse({})
