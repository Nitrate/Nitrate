# -*- coding: utf-8 -*-

from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.simplejson import dumps as json_dumps

from tcms.core.models import TCMSLog
from tcms.core.responses import HttpJSONResponse
from tcms.core.views import Prompt
from tcms.testcases.forms import SearchCaseForm, QuickSearchCaseForm
from tcms.testcases.models import TestCase
from tcms.testcases.models import TestCaseCategory
from tcms.testcases.models import TestCasePlan
from tcms.testcases.models import TestCaseStatus
from tcms.testcases.views import get_selected_testcases
from tcms.testplans.forms import ImportCasesViaXMLForm


MODULE_NAME = 'testplans'


class CaseActions(object):
    '''Actions for operating cases in TestPlan'''

    def __init__(self, request, tp):
        self.__all__ = ['link_cases',
                        'delete_cases',
                        'order_cases',
                        'import_cases']
        self.request = request
        self.REQ = self.request.REQUEST
        self.tp = tp
        self.succeed_response = {'rc': 0, 'response': 'ok'}

    def link_cases(self, template_name='plan/search_case.html'):
        '''Handle to form to add case to plans'''
        SUB_MODULE_NAME = 'plans'
        tcs = None

        do_action = self.REQ.get('action')

        if do_action == 'add_to_plan':
            if self.request.user.has_perm('testcases.add_testcaseplan'):
                cases_ids = self.REQ.getlist('case')
                tcs = TestCase.objects.filter(case_id__in=cases_ids).only('pk')

                for tc in tcs.iterator():
                    self.tp.add_case(tc)
            else:
                return HttpResponse("Permission Denied")

            return HttpResponseRedirect(
                reverse('tcms.testplans.views.get', args=[self.tp.pk]))

        search_mode = self.REQ.get('search_mode')
        if do_action == 'search':
            if search_mode == 'quick':
                form = quick_form = QuickSearchCaseForm(self.REQ)
                normal_form = SearchCaseForm()
            else:
                form = normal_form = SearchCaseForm(self.REQ)
                form.populate(product_id=self.REQ.get('product'))
                quick_form = QuickSearchCaseForm()

            if form.is_valid():
                tcs = TestCase.list(form.cleaned_data)
                tcs = tcs.select_related(
                    'author', 'default_tester', 'case_status',
                    'priority', 'category', 'tag__name'
                ).only('pk', 'summary', 'create_date',
                       'author__email', 'default_tester__email',
                       'case_status__name', 'priority__value',
                       'category__name', 'tag__name')
                tcs = tcs.exclude(
                    case_id__in=self.tp.case.values_list('case_id',
                                                         flat=True))
        else:
            normal_form = SearchCaseForm(initial={
                'product': self.tp.product_id,
                'product_version': self.tp.product_version_id,
                'case_status_id': TestCaseStatus.get_CONFIRMED()
            })
            quick_form = QuickSearchCaseForm()

        # FIXME: when run here, action is unknown aciton and should be invalid,
        # how to handle this situation?

        context_data = {
            'module': MODULE_NAME,
            'sub_module': SUB_MODULE_NAME,
            'test_plan': self.tp,
            'test_cases': tcs,
            'search_form': normal_form,
            'quick_form': quick_form,
            'search_mode': search_mode
        }

        ctx = RequestContext(self.request)
        return render_to_response(template_name, context_data,
                                  context_instance=ctx)

    def delete_cases(self):
        '''Just cut off the relationship between plan and case, not deletion'''
        if not self.REQ.get('case'):
            ajax_response = {
                'rc': 1,
                'response': 'At least one case is required to delete.',
            }
            return HttpJSONResponse(json_dumps(ajax_response))

        tcs = get_selected_testcases(self.request).only('pk')

        # Log Action
        tp_log = TCMSLog(model=self.tp)

        for tc in tcs.iterator():
            log_action = 'Remove case {0} from plan {1}'.format(tc.pk,
                                                                self.tp.pk)
            tp_log.make(who=self.request.user, action=log_action)

            log_action = 'Remove from plan {0}'.format(self.tp.pk)
            tc.log_action(who=self.request.user, action=log_action)

            self.tp.delete_case(tc)

        return HttpJSONResponse(json_dumps(self.succeed_response))

    def order_cases(self):
        '''Resort case with new order'''
        # Current we should rewrite all of cases belong to the plan.
        # Because the cases sortkey in database is chaos,
        # Most of them are None.

        if not self.REQ.get('case'):
            ajax_response = {
                'rc': 1,
                'reponse': 'At least one case is required to re-order.',
            }
            return HttpJSONResponse(json_dumps(ajax_response))

        tc_pks = self.REQ.getlist('case')
        tcs = TestCase.objects.filter(pk__in=tc_pks).only('pk')

        for tc in tcs.iterator():
            new_sort_key = (tc_pks.index(str(tc.pk)) + 1) * 10
            TestCasePlan.objects.filter(plan=self.tp, case=tc).update(
                sortkey=new_sort_key)

        return HttpJSONResponse(json_dumps(self.succeed_response))

    def import_cases(self):
        '''Import cases from an XML document'''
        plan_url = reverse('tcms.testplans.views.get', args=[self.tp.pk])
        redirect_to = '{0}#testcases'.format(plan_url)

        INITIAL_TEXT_VERSION = 1

        if self.request.method == 'POST':
            # Process import case from XML action
            if not self.request.user.has_perm('testcases.add_testcaseplan'):
                return HttpResponse(Prompt.render(
                    request=self.request,
                    info_type=Prompt.Alert,
                    info='Permission denied',
                    next=plan_url,
                ))

            xml_form = ImportCasesViaXMLForm(self.REQ,
                                             self.request.FILES)

            if xml_form.is_valid():
                i = 0
                for case in xml_form.cleaned_data['xml_file']:
                    i += 1

                    # Get the case category from the case and related to
                    # the product of the plan
                    try:
                        category = TestCaseCategory.objects.get(
                            product=self.tp.product, name=case['category_name']
                        )
                    except TestCaseCategory.DoesNotExist:
                        category = TestCaseCategory.objects.create(
                            product=self.tp.product, name=case['category_name']
                        )

                    # Start to create the objects
                    tc = TestCase.objects.create(
                        is_automated=case['is_automated'],
                        script=None,
                        arguments=None,
                        summary=case['summary'],
                        requirement=None,
                        alias=None,
                        estimated_time=0,
                        case_status_id=case['case_status_id'],
                        category_id=category.id,
                        priority_id=case['priority_id'],
                        author_id=case['author_id'],
                        default_tester_id=case['default_tester_id'],
                        notes=case['notes'])
                    TestCasePlan.objects.create(plan=self.tp,
                                                case=tc,
                                                sortkey=i * 10)

                    tc.add_text(case_text_version=INITIAL_TEXT_VERSION,
                                author=case['author'],
                                action=case['action'],
                                effect=case['effect'],
                                setup=case['setup'],
                                breakdown=case['breakdown'])

                    # handle tags
                    if case['tags']:
                        for tag in case['tags']:
                            tc.add_tag(tag=tag)

                    # FIXME: duplicated with above creation of TestCasePlan
                    tc.add_to_plan(plan=self.tp)

                return HttpResponseRedirect(redirect_to)
            else:
                return HttpResponse(Prompt.render(
                    request=self.request,
                    info_type=Prompt.Alert,
                    info=xml_form.errors,
                    next=redirect_to,
                ))
        else:
            return HttpResponseRedirect(redirect_to)
