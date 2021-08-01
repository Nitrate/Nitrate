/* global caseDetailExpansionHandler, SimpleCaseRunDetailExpansion, PlanCaseRunsExpansion */
/* global RIGHT_ARROW, DOWN_ARROW */

Nitrate.TestCases = {};
Nitrate.TestCases.Search = {};
Nitrate.TestCases.List = {};
Nitrate.TestCases.AdvancedSearch = {};
Nitrate.TestCases.Details = {};
Nitrate.TestCases.Create = {};
Nitrate.TestCases.Edit = {};
Nitrate.TestCases.Clone = {};

Nitrate.TestCases.SearchResultTableSettings = Object.assign({}, Nitrate.DataTable.commonSettings, {

  // By default, cases are sorted by create_date in desc order.
  // It is equal to set the pk column in the DataTable initialization.
  aaSorting: [[ 2, 'desc' ]],

  oLanguage: {
    sEmptyTable: 'No cases found.'
  },

  aoColumns: [
    {'bSortable': false, 'sClass': 'expandable'},   // the expand/collapse control
    {'bSortable': false},                           // case selector checkbox
    null,                                           // ID
    {'sClass': 'expandable'},                       // Summary
    null,                                           // Author
    null,                                           // Default tester
    null,                                           // Automated
    null,                                           // Status
    null,                                           // Category
    null,                                           // Priority
    null,                                           // Created on
  ],

  fnDrawCallback: function () {
    // Add the ajax_loading row to show case details
    this.fnGetNodes().forEach(function (tr) {
      let caseId = jQ(tr).data('pk');
      jQ(tr).after(jQ(
        '<tr class="case_content hide" style="display: none;">' +
        '<td colspan="' + tr.children.length + '">' +
        '<div id="id_loading_' + caseId + '" class="ajax_loading"></div>' +
        '</td>' +
        '</tr>'
      ));
    });

    jQ('#testcases_table tbody tr td:nth-child(2)').shiftcheckbox({
      checkboxSelector: ':checkbox',
      selectAll: '#testcases_table .js-select-all'
    });

    jQ('#testcases_table tbody :checkbox').on('change', function () {
      Nitrate.TestCases.Search.setActionButtonsStatus(
        jQ('#testcases_table tbody :checkbox:checked').length === 0
      );
    });

    jQ('.expandable').on('click', caseDetailExpansionHandler);
  },

  fnInfoCallback: function (oSettings, iStart, iEnd, iMax, iTotal, sPre) {
    return 'Showing ' + (iEnd - iStart + 1) + ' of ' + iTotal + ' cases';
  }
});

/**
 * Initialize test cases search result table and associated action buttons.
 *
 * @param {string} searchEndpoint - the search endpoint.
 */
Nitrate.TestCases.Search.initializeSearchResult = function (searchEndpoint) {
  jQ('#id_blind_all_link').on('click', function () {
    if (!jQ('div[id^="id_loading_"]').length) {
      jQ(this).removeClass('locked');
    }
    if (jQ(this).is('.locked')) {
      //To disable the 'expand all' until all case runs are expanded.
      return false;
    } else {
      jQ(this).addClass('locked');
      let element = jQ(this).children()[0];
      if (jQ(element).is('.collapse-all')) {
        this.title = 'Collapse all cases';
        blinddownAllCases(element);
      } else {
        this.title = 'Expand all cases';
        blindupAllCases(element);
      }
    }
  });

  jQ('#testcases_table .js-select-all').on('change', function () {
    Nitrate.TestCases.Search.setActionButtonsStatus(!this.checked);
  });

  if (window.location.hash === '#expandall') {
    blinddownAllCases();
  }

  let urls = Nitrate.TestCases.Search.ActionUrls;

  jQ('.js-printable-cases').on('click', function () {
    postToURL(urls.printableCasesUrl, Nitrate.Utils.formSerialize(this.form));
  });

  jQ('.js-export-cases').on('click', function () {
    postToURL(urls.exportCasesUrl, Nitrate.Utils.formSerialize(this.form));
  });

  jQ('#testcases_table').dataTable(
    Object.assign({}, Nitrate.TestCases.SearchResultTableSettings, {
      iDeferLoading: Nitrate.TestCases.Search.numberOfCases,
      sAjaxSource: searchEndpoint + window.location.search,
    })
  );
};

/**
 * Set action buttons' status
 *
 * @param {boolean} disabled - true for disable, otherwise enable them.
 */
Nitrate.TestCases.Search.setActionButtonsStatus = function (disabled) {
  jQ('.js-clone-cases').prop('disabled', disabled);
  jQ('.js-export-cases').prop('disabled', disabled);
  jQ('.js-printable-cases').prop('disabled', disabled);
};

Nitrate.TestCases.List.on_load = function () {
  registerProductAssociatedObjectUpdaters(
    document.getElementById('id_product'),
    false,
    [
      {
        func: getCategoriesByProductId,
        targetElement: document.getElementById('id_category'),
        addBlankOption: true
      },
      {
        func: getComponentsByProductId,
        targetElement: document.getElementById('id_component'),
        addBlankOption: true
      }
    ]
  );

  Nitrate.TestCases.Search.initializeSearchResult('/cases/search/');
};

Nitrate.TestCases.AdvancedSearch.on_load = function () {
  Nitrate.TestCases.Search.initializeSearchResult('/advance-search/');
};

Nitrate.TestCases.Details.bindIssueOperationHandlers = function () {
  jQ('.js-remove-issue').on('click', function (event) {
    removeCaseIssue(this.dataset.issueKey, this.dataset.caseId, this.dataset.caseRunId);
  });

  jQ('.js-add-issue').on('click', function () {
    addCaseIssue(document.getElementById('id_case_issue_form'));
  });
};

Nitrate.TestCases.Details.on_load = function () {
  let caseId = Nitrate.TestCases.Instance.pk;

  let tagsView = new CaseTagsView(caseId);
  tagsView.get();

  jQ('li.tab a').on('click', function () {
    jQ('div.tab_list').hide();
    jQ('li.tab').removeClass('tab_focus');
    jQ(this).parent().addClass('tab_focus');
    jQ('#' + this.title).show();
  });

  if (window.location.hash) {
    jQ('a[href="' + window.location.hash + '"]').trigger('click');
  }

  jQ('#id_add_component').on('click', function () {
    if (this.disabled) {
      return false;
    }

    let params = {
      'case': Nitrate.TestCases.Instance.pk,
      'product': Nitrate.TestCases.Instance.product_id,
      'category': Nitrate.TestCases.Instance.category_id
    }
    renderComponentForm(getDialog(), params, function (e) {
      e.stopPropagation();
      e.preventDefault();

      let params = Nitrate.Utils.formSerialize(this);
      params['case'] = Nitrate.TestCases.Instance.pk;
      postRequest({url: '/cases/add-component/', data: params, traditional: true});
    });
  });

  jQ('#id_remove_component').on('click', function () {
    let params = Nitrate.Utils.formSerialize(this.form);
    if (params.component.length === 0) {
      return;
    }
    confirmDialog({
      message: defaultMessages.confirm.remove_case_component,
      title: 'Manage Components',
      yesFunc: function () {
        postRequest({
          url: '/cases/remove-component/',
          traditional: true,
          data: {
            'case': Nitrate.TestCases.Instance.pk,
            'o_component': params.component
          }
        });
      }
    });
  });

  jQ('.link_remove_component').on('click', function () {
    confirmDialog({
      message: defaultMessages.confirm.remove_case_component,
      title: 'Manage Components',
      yesFunc: function () {
        postRequest({
          url: '/cases/remove-component/',
          traditional: true,
          forbiddenMessage: 'You are not allowed to add issue to case.',
          data: {
            'case': Nitrate.TestCases.Instance.pk,
            'o_component': jQ('input[name="component"]')[
              jQ('.link_remove_component').index(this)
            ].value
          },
        });
      }
    });
  });

  jQ('#case-components-table tbody tr td:nth-child(1)').shiftcheckbox({
    checkboxSelector: ':checkbox',
    selectAll: '#case-components-table .js-select-all'
  });

  jQ('.plan_expandable').on('click', function () {
    new PlanCaseRunsExpansion(this).toggle(function () {
      jQ('#table_case_runs_by_plan .expandable').on('click', function () {
        new SimpleCaseRunDetailExpansion(this).toggle();
      });
    });
  });

  jQ('#btn_edit,#btn_clone').on('click', function () {
    window.location.href = jQ(this).data('link');
  });

  // jQ('.js-remove-issue').on('click', function (event) {
  //   removeCaseIssue(this.dataset.issueKey, this.dataset.caseId, this.dataset.caseRunId);
  // });
  //
  // jQ('.js-add-issue').on('click', function () {
  //   addCaseIssue(jQ('#id_case_issue_form')[0]);
  // });

  Nitrate.TestCases.Details.bindIssueOperationHandlers();

  jQ('#issue_key').on('keydown', function (event) {
    addCaseIssueViaEnterKey(jQ('#id_case_issue_form')[0], event);
  });
};

/*
 * Resize all editors within the webpage after they are rendered.
 * This is used to avoid a bug of TinyMCE in Firefox 11.
 */
function resizeTinymceEditors() {
  jQ('.mceEditor .mceIframeContainer iframe').each(function () {
    let elem = jQ(this);
    elem.height(elem.height() + 1);
  });
}

Nitrate.TestCases.Create.on_load = function () {
  SelectFilter.init('id_component', 'component', 0, '/static/admin/');

  jQ('#id_product').change(function () {
    let from = 'id_component_from';
    let to = 'id_component_to';
    let fromField = jQ('#' + from)[0];
    let toField = jQ('#' + to)[0];
    jQ(toField).html('');
    let selectedProductId = jQ('#id_product').val();

    getComponentsByProductId(selectedProductId, fromField, false, function () {
      SelectBox.cache[from] = [];
      SelectBox.cache[to] = [];
      let node = null;
      for (let i = 0; (node = fromField.options[i]); i++) {
        SelectBox.cache[from].push({value: node.value, text: node.text, displayed: 1});
      }
    });

    getCategoriesByProductId(selectedProductId, document.getElementById('id_category'), false);
  });

  jQ('#id_product').trigger('change');

  resizeTinymceEditors();

  jQ('.js-case-cancel').on('click', function () {
    window.history.go(-1);
  });

  jQ('.js-case-cancel').on('click', function () {
    window.location.assign(this.dataset.actionUrl);
  });

};

Nitrate.TestCases.Edit.on_load = function () {
  registerProductAssociatedObjectUpdaters(
    document.getElementById('id_product'),
    false,
    [
      {
        func: getCategoriesByProductId,
        targetElement: document.getElementById('id_category'),
        addBlankOption: false
      }
    ]
  );

  resizeTinymceEditors();

  jQ('.js-back-button').on('click', function () {
    window.history.go(-1);
  });
};

Nitrate.TestCases.Clone.on_load = function () {
  registerProductAssociatedObjectUpdaters(
    document.getElementById('id_product'),
    false,
    [
      {
        func: getVersionsByProductId,
        targetElement: document.getElementById('id_product_version'),
        addBlankOption: true
      }
    ]
  );

  jQ('#id_form_search_plan').on('submit', function (e) {
    e.stopPropagation();
    e.preventDefault();

    let container = jQ('#id_plan_container');
    container.show();

    let thisform = e.target;
    sendHTMLRequest({
      url: thisform.action,
      method: thisform.method,
      data: jQ(this).serialize(),
      container: container,
    });
  });

  jQ('#id_use_filterplan').on('click', function () {
    jQ('#id_form_search_plan :input').prop('disabled', false);
    jQ('#id_plan_id').val('');
    jQ('#id_plan_id').prop('name', '');
    jQ('#id_copy_case').prop('checked', true);
  });

  if (jQ('#id_use_sameplan').length) {
    jQ('#id_use_sameplan').on('click', function () {
      jQ('#id_form_search_plan :input').prop('disabled', true);
      jQ('#id_plan_id').val(jQ('#value_plan_id').val());
      jQ('#id_plan_id').prop('name', 'plan');
      jQ('#id_plan_container').html(constructAjaxLoading()).hide();
      jQ('#id_copy_case').prop('checked', false);
    });
  }

  jQ('.js-cancel-button').on('click', function () {
    window.history.go('-1');
  });

};

/**
 * A function bound to AJAX request success event to add or remove issue to and from a case. It
 * displays the issues table returned from the backend, and bind necessary event handlers, count and
 * display current number of issues added to case already.
 *
 * @param {object} data - an object containing the data to display.
 * @param {string} data.html - a piece of HTML containing the issues table.
 */
function issueOperationSuccessCallback(data) {
  jQ('div#issues').html(data.html);
  jQ('#case_issues_count').text(jQ('table#issues').prop('count'));
  Nitrate.TestCases.Details.bindIssueOperationHandlers();
}


function addCaseIssue(form) {
  let addIssueForm = jQ(form);
  let issueKey = addIssueForm.find('input#issue_key').val().trim();

  let selectedIssueTrackerOption = addIssueForm.find('option:selected');
  let issueKeyRegex = selectedIssueTrackerOption.data('issue-key-regex');
  if (! RegExp(issueKeyRegex).test(issueKey)) {
    showModal('Issue key is malformat.', 'Input Error');
    return;
  }

  if (!issueKey.length) {
    // No bug ID input, no any response is required
    return false;
  }

  postRequest({
    url: form.action,
    data: {
      issue_key: issueKey,
      tracker: parseInt(selectedIssueTrackerOption.val())
    },
    success: issueOperationSuccessCallback,
    forbiddenMessage: 'You are not allowed to add issue to case.',
  });
}

function removeCaseIssue(issueKey, caseId, caseRunId) {
  confirmDialog({
    message: 'Are you sure to remove issue ' + issueKey + '?',
    title: 'Manage Issues',
    yesFunc: function () {
      postRequest({
        url: '/case/' + caseId + '/issues/delete/',
        data: {issue_key: issueKey, case_run: caseRunId},
        success: issueOperationSuccessCallback,
        forbiddenMessage: 'You are not allowed to remove issue from case.',
      });
    }
  });
}


/**
 * Handle triggered by click event of Remove button to remove a plan from a
 * case' plans table. This is bound to specific element in the template directly.
 *
 * @param {number} caseId - the case id.
 * @param {HTMLButtonElement} button - the element this handler is bound to.
 */
function removePlanFromPlansTableHandler(caseId, button) {
  confirmDialog({
    message: 'Are you sure to remove the case from this plan?',
    yesFunc: function () {
      postRequest({
        url: '/case/' + caseId + '/plans/remove/',
        data: {plan: parseInt(jQ(button).data('planid'))},
        success: function (data) {
          jQ('#plan').html(data.html);
          jQ('#plan_count').text(jQ('table#testplans_table').prop('count'));
        },
      });
    }
  });
}

/**
 * Handler triggered by the form submit event to add plans to the case. This is
 * called in form submit event directly in the template.
 *
 * @param {number} caseId - the case id.
 * @param {HTMLFormElement} form - the form element containing elements having plan ids.
 */
function addCaseToPlansHandler(caseId, form) {
  let planIds = form.elements['pk__in'].value.trim();

  if (planIds.length === 0) {
    showModal(defaultMessages.alert.no_plan_specified, 'Missing something?');
    return;
  }

  let casePlansUrl = '/case/' + caseId + '/plans/';

  previewPlan({pk__in: planIds}, casePlansUrl, function (e) {
    e.stopPropagation();
    e.preventDefault();

    let planIds = Nitrate.Utils.formSerialize(this).plan_id;
    if (!planIds) {
      showModal(defaultMessages.alert.no_plan_specified, 'Missing something?');
      return false;
    }

    clearDialog();

    postRequest({
      url: casePlansUrl + 'add/',
      data: {plan: planIds},
      traditional: true,
      success: function (data) {
        jQ('#plan').html(data.html);
        jQ('#plan_count').text(jQ('table#testplans_table').prop('count'));
      },
    });
  });
}

function addCaseIssueViaEnterKey(element, e) {
  if (e.keyCode === 13) {
    addCaseIssue(element);
  }
}

/**
 * Toggle case runs by plan
 *
 * @param {object} params - an object containing information to toggle case runs.
 * @param {string|HTMLElement} params.c_container - the container containing all the content
 *                                                  including case runs.
 * @param {string|HTMLElement} params.container - the container containing case runs.
 * @param {number} params.case_id - the case id.
 * @param {number} params.case_run_plan_id - the plan id.
 * @param {Function} [callback] - a callback function passed to argument `callbackAfterFillIn` of
 *                                function `sendHTMLRequest`.
 */
function toggleCaseRunsByPlan(params, callback) {
  let contentContainer = typeof params.c_container === 'string' ?
    jQ('#' + params.c_container) : jQ(params.c_container);

  contentContainer.toggle();

  if (jQ('#id_loading_' + params.case_run_plan_id).length) {
    sendHTMLRequest({
      url: '/case/' + params.case_id + '/caserun-list-pane/',
      data: {plan_id: params.case_run_plan_id},
      container: contentContainer[0],
      callbackAfterFillIn: callback,
    });
  }

  let container = typeof params.container === 'string' ?
    jQ('#' + params.container) : jQ(params.container);

  let blindIcon = container.find('img').first();
  if (contentContainer.is(':hidden')) {
    blindIcon.removeClass('collapse').addClass('expand').prop('src', RIGHT_ARROW);
  } else {
    blindIcon.removeClass('expand').addClass('collapse').prop('src', DOWN_ARROW);
  }
}
