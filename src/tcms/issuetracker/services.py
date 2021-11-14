# -*- coding: utf-8 -*-

import importlib
import io
import logging
import urllib.parse

from tcms.issuetracker.models import Issue, IssueTracker, ProductIssueTrackerRelationship
from tcms.issuetracker.task import bugzilla_external_track

log = logging.getLogger(__name__)


def find_service(issue_tracker):
    """
    Find out corresponding service class of issue tracker model and return
    initialized object.

    :param issue_tracker: find corresponding service of this issue tracker.
    :type issue_tracker: :class:`IssueTracker`
    :return: instance of service class.
    :rtype: a concrete class of :class:`IssueTrackerService`
    :raises ValueError: if missing issue tracker's ``class_path`` to find
        corresponding service.
    """
    if not issue_tracker.class_path:
        raise ValueError(
            "class_path must be set in order to find a corresponding service."
            " Refer to IssueTracker.class_path help text."
        )
    module_path, _, class_name = issue_tracker.class_path.rpartition(".")
    module = importlib.import_module(module_path)
    return getattr(module, class_name)(issue_tracker)


class IssueTrackerService:
    """Base issue tracker service

    Define and implement base functionalities for an issue tracker service. It
    is not recommended to initialize object from this class directly. Instead,
    call factory method :meth:`find_service` to get a new service object.

    A concrete subclass can divide from this base class to implement for
    specific issue tracker service. Please refer to each method's docstring to
    learn what you can customize.

    :param tracker_model: the model object of an issue tracker.
    :type tracker_model: :class:`IssueTracker`
    """

    def __init__(self, tracker_model):
        self._model = tracker_model

    @property
    def tracker_model(self) -> IssueTracker:
        """Property to access issue tracker model"""
        return self._model

    def link_external_tracker(self, issue):
        """Add case link to an issue's external tracker

        Some issue tracker product, like Bugzilla, allows to define external
        trackers in order to relative external resources for an issue. Instead
        of adding a case ID into issue, Nitrate allows to add case ID to an
        issue in that kind of external trackers.

        However, what does the issue's external tracker look like? It depends.
        Some issue tracker might be different without similar external tracker
        like Bugzilla supports. In such case, developer has to handle the
        concrete case for specific case.

        Subclass for specific issue tracker is responsible for implement this
        method.

        :param issue: an issue whose relative case ID will be added to this
            issue's external tracker.
        :type issue: :class:`Issue <tcms.issuetracker.models.Issue>`
        """
        log.info("This is default behavior of add_external_tracker which does nothing.")

    def make_issue_report_url(self, case_run):
        """Make issue report URL

        Issue report URL is used to file an issue in a specific issue tracker.
        Any concrete issue tracker services derived from
        :class:`IssueTrackerService` could override this method or relative
        private methods to customize the final URL.

        :param case_run: a case run for which to file an issue. The needed data
            could be retrieved through relationship path from this case run.
        :type case_run: :class:`TestCaseRun <tcms.testruns.models.TestCaseRun>`
        :return: a complete URL to file an issue.
        :rtype: str
        """
        url_args = self._prepare_issue_report_url_args(case_run)
        return "{}/{}{}".format(
            self.tracker_model.service_url.rstrip("/"),
            self.tracker_model.issue_report_endpoint.lstrip("/"),
            "?" + urllib.parse.urlencode(url_args, True) if url_args else "",
        )

    def add_issue(
        self,
        issue_key,
        case,
        case_run=None,
        summary=None,
        description=None,
        add_case_to_issue=None,
    ):
        """Add new issue

        An issue could be associated with a single case or with a case and
        corresponding case run together.

        :param str issue_key: issue key to add.
        :param case: issue key will be added to this case.
        :type case: :class:`TestCase <tcms.testcases.models.TestCase>`
        :param case_run: optional case run. If passed, issue is associated
            with this case run as well.
        :type case_run: :class:`TestCaseRun <tcms.testruns.models.TestCaseRun>`
        :param str summary: optional summary of this issue.
        :param str description: optional description of this issue.
        :param bool add_case_to_issue: whether to link case to issue tracker's
            external tracker. Defaults to not link test case to the new issue,
            however if it is required, :meth:`link_external_tracker` has to be
            called explicitly.
        :return: the newly created issue.
        :rtype: :class:`Issue <tcms.issuetracker.models.Issue>`
        :raises ValidationError: if fail to validate the new issue.
        """
        issue = Issue(
            issue_key=issue_key,
            tracker=self.tracker_model,
            case=case,
            case_run=case_run,
            summary=summary,
            description=description,
        )
        issue.full_clean()
        issue.save()
        if self.tracker_model.allow_add_case_to_issue and add_case_to_issue:
            self.link_external_tracker(issue)
        return issue

    def format_issue_report_content(self, build_name, case_text):
        """Format issue report content with a set of information

        This method works with ``IssueTracker.issue_report_templ`` and provides
        a set of information to format issue report content. Please refer to
        the implementation to know what format arguments are provided
        currently.

        Subclasses for specific issue tracker services could override it to
        format content in different way.

        :param str build_name: the build name.
        :param case_text: a case' text object. The report content could be
            formatted with text provided by this object.
        :type case_text: :class:`TestCaseText` or :class:`NoneText`
        :return: formatted issue report content which then can be encoded and
            be a part of issue report URL argument.
        :rtype: str
        """
        return self.tracker_model.issue_report_templ.format(
            build_name=build_name,
            setup=case_text.setup or "# Fill setup here ...",
            action=case_text.action or "# Fill action here ...",
            effect=case_text.effect or "# Fill effect here ...",
        )

    def get_stock_issue_report_args(self, case_run):
        """
        Get service supported issue report arguments and their values in
        key/value pair.

        Define and return what issue report arguments and their default value
        current issue tracker service supports. This is useful for someone,
        might be a Nitrate administrator who has proper permissions to manage
        issue tracker, to select part or all arguments to define the lines in
        ``IssueTracker.issue_report_params``.

        Subclass could override this method to customize the for a specific
        issue tracker.

        :param case_run: a test case run whose relative objects through
            ORM relationship could be used to customize arguments' value.
        :type case_run: :class:`TestCaseRun`
        :return: a mapping containing stock issue report URL format arguments.
        :rtype: dict[str, str]
        """
        return {}

    def get_extra_issue_report_url_args(self, case_run):
        """Get extra issue report URL arguments

        This is where to construct and return extra issue report URL arguments
        which are not able to be defined in
        ``IssueTracker.issue_report_params``. For example, some arguments are
        already defined in that field, and Nitrate also needs to support other
        custom fields for a specific issue tracker service, e.g.,
        ``cf_field_a``, and the logic to construct their values would be more
        complicated than just giving a simple value directly, developer could
        divide from class :class:`IssueTrackerService` and override this method
        to provide those custom fields.

        Note that, any argument listed in ``IssueTracker.issue_report_params``
        will overwrite the one in extras.

        :param case_run: a test case run from which to get required information
            for supported issue report URL arguments.
        :type case_run: :class:`TestCaseRun`
        :return: a mapping whose key is argument name and value is the argument
            value. It is not necessary to consider URL encode here.
        :rtype: dict[str, str]
        """
        return {}

    def _fill_values_to_predefined_issue_report_url_args(self, stock_args):
        """Convert predefined issues report URL arguments with stock arguments

        Nitrate provides a few URL arguments. The final issue report URL
        arguments will be generated with the stock arguments and those defined
        in issue tracker object in the database.

        :param stock_args: supported URL arguments by specific issue
            tracker service. Nitrate will look up from these supported
            arguments and fill found value into Argument listed in
            ``IssueTracker.issue_report_params``.
        :type stock_args: dict[str, str]
        :return: a mapping containing merged issue report URL arguments.
        :rtype: dict[str, str]
        """
        result = dict()
        buf = io.StringIO(self.tracker_model.issue_report_params)
        arg_lines = buf.readlines()
        buf.close()
        for line in arg_lines:
            arg_name, arg_value = line.split(":", 1)
            arg_value = arg_value.strip()
            is_constant_arg = arg_value != ""
            if is_constant_arg:
                result[arg_name] = arg_value
            else:
                stock_value = stock_args.get(arg_name)
                if stock_value is None:
                    log.warning(
                        "Nitrate does not provide issue report URL argument %s",
                        arg_name,
                    )
                else:
                    result[arg_name] = stock_value
        return result

    def _prepare_issue_report_url_args(self, case_run):
        """Prepare issue report URL arguments

        This is the method to prepare URL arguments used to construct issue
        report URL. It works for most cases generally. For specific issue
        tracker service implementation, developer has opportunity to change
        arguments which works for itself by overriding
        :meth:`_get_issue_report_url_args` and
        :meth:`_get_stock_issue_report_args`.

        :param case_run: the case run for which to file issue. Some argument
            might be set to have internal object's value, for example product
            name, a ``case_run`` object has the relationship path to access
            required relative data, e.g. case, run, plan, product, etc.
        :type case_run: :class:`TestRunCase`
        :return: a mapping containing URL arguments that can be used to
            construct URL query string part.
        :rtype: dict[str, str]
        """
        args = self.get_extra_issue_report_url_args(case_run)
        url_args = self.get_stock_issue_report_args(case_run)
        args.update(self._fill_values_to_predefined_issue_report_url_args(url_args))
        return args

    def make_issues_display_url(self, issue_keys):
        """Make URL linking to issue tracker to display issues

        This requires issue tracker's ``issues_display_url_fmt`` is set, which
        accepts a string format argument ``issue_keys``.

        By default, issue keys are concatenated and separated by comma. This
        should work for most of kind of issue tracker product, for example,
        Bugzilla and JIRA. However, if it does not work for some other issue
        tracker, developer has to subclass ``IssueTrackerService`` and override
        this method to construct the display URL.

        :param issue_keys: list of issue keys.
        :type issue_keys: list[str]
        :return: the display URL which could be opened in Web browser to
            display specified issues.
        :rtype: str
        """
        return self.tracker_model.issues_display_url_fmt.format(
            issue_keys=",".join(map(str, issue_keys))
        )


class Bugzilla(IssueTrackerService):
    """Represent general Bugzilla issue tracker"""

    def get_extra_issue_report_url_args(self, case_run):
        """Get extra URL arguments for reporting issue in Bugzilla"""
        args = super().get_extra_issue_report_url_args(case_run)

        case_text = case_run.get_text_with_version(case_text_version=case_run.case_text_version)
        args["comment"] = self.format_issue_report_content(case_run.build.name, case_text)
        return args

    def get_stock_issue_report_args(self, case_run):
        """Get issue report arguments Bugzilla supports

        For filing a bug in a Bugzilla service, following arguments are
        supported:

        * ``short_desc``: content of bug summary.
        * ``version``: product version.
        * ``component``: selected component.
        * ``product``: selected product name.

        For the details of parameters and return value, please refer to
        :meth:`IssueTrackerService.get_stock_issue_report_args`.
        """
        case = case_run.case
        run = case_run.run
        product = run.plan.product
        args = {
            "short_desc": f"Test case failure: {case.summary}",
            "version": run.product_version.value,
            # product will be determined later below
            # This is the default value provided, but it could be changed below.
            "component": list(case.component.values_list("name", flat=True)),
        }

        # Things could be different in real world when use various kind of
        # Bugzilla instances. Nitrate is trying to do best to return URL
        # arguments according to the configuration defined in relationship
        # between product and issue tracker.

        try:
            rel = ProductIssueTrackerRelationship.objects.get(
                product=product, issue_tracker=self.tracker_model
            )
        except ProductIssueTrackerRelationship.DoesNotExist:
            log.warning(
                "Issue tracker %r is not associated with any product. This "
                "should not happen in practice. Please check configuration in "
                "a concrete issue tracker's admin page.",
                self.tracker_model,
            )
            # NOTE: Nitrate does not try to be smart for the product value here.
            # When configuration is correct, product name could be another
            # choice to be the namespace or the alias. But, if config is not
            # completed, just not put argument product in the URL, which should
            # work in most Bugzilla instances where allow user to select a
            # product manually instead of reporting product name is unknown.
            return args

        if rel.namespace:
            args["product"] = rel.namespace
            args["component"] = rel.alias or product.name
        else:
            args["product"] = rel.alias or product.name

        return args


class RHBugzilla(IssueTrackerService):
    """Representing Red Hat Bugzilla"""

    def get_extra_issue_report_url_args(self, case_run):
        """Add URL arguments which are specific to Red Hat Bugzilla"""
        args = super().get_extra_issue_report_url_args(case_run)
        args["cf_build_id"] = case_run.run.build.name
        return args

    def link_external_tracker(self, issue: Issue) -> None:
        """Link case to issue's external tracker in remote Bugzilla service"""
        bugzilla_external_track(
            self.tracker_model.api_url,
            self.tracker_model.credential,
            issue.issue_key,
            issue.case.pk,
        )


class JIRA(IssueTrackerService):
    """Represent general JIRA issue tracker"""
