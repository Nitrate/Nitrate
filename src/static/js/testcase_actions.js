Nitrate.TestCases = {};
Nitrate.TestCases.List = {};
Nitrate.TestCases.AdvanceList = {};
Nitrate.TestCases.Details = {};
Nitrate.TestCases.Create = {};
Nitrate.TestCases.Edit = {};
Nitrate.TestCases.Clone = {};

Nitrate.TestCases.AdvanceList.on_load = function () {
  jQ('#testcases_table :checkbox').on('change', function () {
    jQ('#case_advance_printable').prop(
      'disabled', jQ('#testcases_table tbody :checkbox:checked').length === 0
    );
  });

  jQ('#testcases_table tbody tr td:nth-child(2)').shiftcheckbox({
    checkboxSelector: ':checkbox',
    selectAll: '#testcases_table .js-select-all'
  });

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

  jQ('.expandable').on('click', function () {
    let c = jQ(this).parent()[0]; // Container
    let cContainer = jQ(c).next()[0]; // Content Containers
    let caseId = jQ(c).find('input[name="case"]')[0].value;

    toggleTestCasePane({
      case_id: caseId,
      casePaneContainer: jQ(cContainer)
    });
    toggleExpandArrow({
      caseRowContainer: jQ(c),
      expandPaneContainer: jQ(cContainer)
    });
  });

  if (window.location.hash === '#expandall') {
    blinddownAllCases();
  }

  let listParams = Nitrate.TestCases.List.Param;
  jQ('#case_advance_printable').on('click', function () {
    postToURL(listParams.case_printable, Nitrate.Utils.formSerialize(this.form));
  });
  jQ('#export_selected_cases').on('click', function () {
    postToURL(listParams.case_export, Nitrate.Utils.formSerialize(this.form));
  });
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

  /* Event handlers of case expansion/collapse */

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

  jQ('#testcases_table tbody tr td.expandable').on('click', function () {
    let tr = jQ(this).parent();
    let caseRowContainer = tr;
    let caseId = caseRowContainer.find('input[name="case"]').prop('value');
    let detailTd = '<tr class="case_content hide" style="display: none;"><td colspan="11">' +
      '<div id="id_loading_' + caseId + '" class="ajax_loading"></div></td></tr>';
    if (!caseRowContainer.next().hasClass('hide')) {
      caseRowContainer.after(detailTd);
    }

    toggleTestCasePane({
      case_id: caseId,
      casePaneContainer: tr.next()
    });
    toggleExpandArrow({
      caseRowContainer: tr,
      expandPaneContainer: tr.next()
    });
  });

  if (window.location.hash === '#expandall') {
    blinddownAllCases();
  }

  /* Initialize cases search result table and relative controls */

  jQ('#testcases_table').dataTable({
    'iDisplayLength': 20,
    'sPaginationType': 'full_numbers',
    'bFilter': false,
    'bLengthChange': false,
    'aaSorting': [[ 2, 'desc' ]],
    'bProcessing': true,
    'bServerSide': true,
    'sAjaxSource': '/cases/ajax/' + this.window.location.search,
    'aoColumns': [
      {'bSortable': false, 'sClass': 'expandable'},
      {'bSortable': false},
      {'sType': 'html', 'sClass': 'expandable'},
      {'sType': 'html', 'sClass': 'expandable'},
      {'sType': 'html', 'sClass': 'expandable'},
      {'sClass': 'expandable'},
      {'sClass': 'expandable'},
      {'sClass': 'expandable'},
      {'sClass': 'expandable'},
      {'sClass': 'expandable'},
      {'sClass': 'expandable'}
    ],
    'fnDrawCallback': function () {
      jQ('#testcases_table tbody tr td:nth-child(2)').shiftcheckbox({
        checkboxSelector: ':checkbox',
        selectAll: '#testcases_table .js-select-all'
      });

      jQ('#testcases_table :checkbox').on('change', function () {
        let disable = jQ('#testcases_table tbody :checkbox:checked').length === 0;
        jQ('#case_list_printable').prop('disabled', disable);
        jQ('#clone_cases').prop('disabled', disable);
        jQ('#export_selected_cases').prop('disabled', disable);
      });
    }
  });

  if (jQ('#id_checkbox_all_case')[0]) {
    jQ('#id_checkbox_all_case').on('click', function () {
      jQ('#case_list_printable').prop('disabled', !this.checked);
    });
  }

  let listParams = Nitrate.TestCases.List.Param;
  jQ('#case_list_printable').on('click', function () {
    postToURL(listParams.case_printable, Nitrate.Utils.formSerialize(this.form));
  });
  jQ('#export_selected_cases').on('click', function () {
    postToURL(listParams.case_export, Nitrate.Utils.formSerialize(this.form));
  });
};

Nitrate.TestCases.Details.on_load = function () {
  let caseId = Nitrate.TestCases.Instance.pk;

  constructTagZone(jQ('#tag')[0], {'case': caseId});

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
    let c = jQ(this).parent();
    toggleCaseRunsByPlan(
      {
        'type' : 'case_run_list',
        'container': c[0],
        'c_container': c.next()[0],
        'case_id': c.find('input').first().val(),
        'case_run_plan_id': c[0].id
      },
      function () {
        jQ('#table_case_runs_by_plan .expandable').on('click', function () {
          let c = jQ(this).parent(); // Container
          // FIXME: case_text_version is not used in the backend to show caserun
          //        information, notes, logs, and comments.
          toggleSimpleCaseRunPane({
            caserunRowContainer: c,
            expandPaneContainer: c.next(),
            caseId: c.find('input[name="case"]')[0].value,
            caserunId: c.find('input[name="case_run"]')[0].value
          });
        });
      });
  });

  jQ('#btn_edit,#btn_clone').on('click', function () {
    window.location.href = jQ(this).data('link');
  });

  jQ('.js-del-button').on('click', function (event) {
    let params = jQ(event.target).data('params');
    deleConfirm(params.attachmentId, params.source, params.sourceId);
  });

  jQ('.js-remove-issue').on('click', function (event) {
    let params = jQ(event.target).data('params');
    removeCaseIssue(params.issueKey, params.caseId, params.caseRunId);
  });

  jQ('.js-add-issue').on('click', function () {
    addCaseIssue(jQ('#id_case_issue_form')[0]);
  });

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
  if (jQ('.js-plan-cancel').length) {
    jQ('.js-plan-cancel').on('click', function () {
      window.location.href = jQ(this).data('param');
    });
  }
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

    sendHTMLRequest({
      url: '/plans/',
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


/*
 * Toggle simple caserun pane in Case Runs tab in case page.
 */
function toggleSimpleCaseRunPane(options) {
  options.expandPaneContainer.toggle();

  if (options.caserunRowContainer.next().find('.ajax_loading').length) {
    sendHTMLRequest({
      url: '/case/' + options.caseId + '/caserun-simple-pane/',
      data: {case_run_id: options.caserunId},
      container: options.expandPaneContainer
    })
  }

  toggleExpandArrow({
    caseRowContainer: options.caserunRowContainer,
    expandPaneContainer: options.expandPaneContainer
  });
}

/**
 * A function bound to AJAX request success event to add or remove issue to and from a case. It
 * displays the issues table returned from the backend, and bind necessary event handlers, count and
 * display current number of issues added to case already.
 * @param {object} data
 * @param {string} data.html - a piece of HTML containing the issues table.
 */
function issueOperationSuccessCallback(data) {
  jQ('div#issues').html(data.html);

  jQ('.js-add-issue').on('click', function () {
    addCaseIssue(jQ('#id_case_issue_form')[0]);
  });
  jQ('.js-remove-issue').on('click', function (event) {
    let params = jQ(event.target).data('params');
    removeCaseIssue(params.issueKey, params.caseId, params.caseRunId);
  });
  jQ('#case_issues_count').text(jQ('table#issues').prop('count'));
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

  getRequest({
    url: form.action,
    data: {
      handle: 'add',
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
      getRequest({
        url: '/case/' + caseId + '/issue/',
        data: {handle: 'remove', issue_key: issueKey, case_run: caseRunId},
        success: issueOperationSuccessCallback,
        forbiddenMessage: 'You are not allowed to remove issue from case.',
      });
    }
  });
}


/* eslint no-unused-vars:off */
/**
 * Handle triggered by click event of Remove button to remove a plan from a
 * case' plans table. This is bound to specific element in the template directly.
 * @param {number} caseId
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
 * @param {number} caseId
 * @param {HTMLFormElement} form
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
 * @param {Object} params
 * @param {string|HTMLElement} params.c_container
 * @param {string|HTMLElement} params.container
 * @param {number} params.case_id
 * @param {number} params.case_run_plan_id
 * @param callback
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
    blindIcon.removeClass('collapse').addClass('expand').prop('src', '/static/images/t1.gif');
  } else {
    blindIcon.removeClass('expand').addClass('collapse').prop('src', '/static/images/t2.gif');
  }
}
