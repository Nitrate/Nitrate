# -*- coding: utf-8 -*-

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import JsonResponse
from django.views import generic
from django.views.decorators.http import require_GET

from tcms.core.responses import JsonResponseBadRequest
from tcms.core.utils import form_errors_to_list

from .forms import AddLinkReferenceForm, BasicValidationForm
from .models import LinkReference, create_link

__all__ = (
    "AddLinkReferenceForm",
    "AddLinkToTargetView",
    "get",
    "RemoveLinkReferenceView",
)


class AddLinkToTargetView(PermissionRequiredMixin, generic.View):
    """Add new link to a specific target

    The target should be a valid model within Nitrate, which are documented in
    ``LINKREF_TARGET``.

    Incoming request should be a POST request, and contains following
    arguments:

    * target: To which the new link will link to. The avialable target names
      are documented in the ``LINKREF_TARGET``.
    * target_id: the ID used to construct the concrete target instance, to
      which the new link will be linked.
    * name: a short description to this new link, and accept 64 characters at
      most.
    * url: the actual URL.
    """

    permission_required = "testruns.change_testcaserun"

    def post(self, request):
        form = AddLinkReferenceForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            url = form.cleaned_data["url"]
            target_id = form.cleaned_data["target_id"]
            model_class = form.cleaned_data["target"]

            model_instance = model_class.objects.get(pk=target_id)
            create_link(name=name, url=url, link_to=model_instance)

            return JsonResponse({"name": name, "url": url})
        else:
            return JsonResponseBadRequest({"message": form.errors.as_text()})


@require_GET
def get(request):
    """Get links of specific instance of content type

    - target: The model name of the instance being searched
    - target_id: The ID of the instance

    Only accept GET request from client.
    """
    form = BasicValidationForm(request.GET)

    if form.is_valid():
        model_class = form.cleaned_data["target"]
        target_id = form.cleaned_data["target_id"]

        try:
            model_instance = model_class.objects.get(pk=target_id)
            links = LinkReference.get_from(model_instance)
        except Exception as err:
            return JsonResponseBadRequest({"message": str(err)})

        jd = []
        for link in links:
            jd.append({"name": link.name, "url": link.url})
        return JsonResponse(jd, safe=False)

    else:
        return JsonResponseBadRequest({"message": form_errors_to_list(form)})


class RemoveLinkReferenceView(PermissionRequiredMixin, generic.View):
    """Remove a specific link with ID"""

    permission_required = "testruns.change_testcaserun"

    def post(self, request, link_id):
        try:
            LinkReference.unlink(link_id)
        except Exception as err:
            return JsonResponseBadRequest({"message": str(err)})

        return JsonResponse({"message": "Link has been removed successfully."})
