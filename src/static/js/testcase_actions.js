Nitrate.TestCases = {};
Nitrate.TestCases.List = {};
Nitrate.TestCases.AdvanceList = {};
Nitrate.TestCases.Details = {};
Nitrate.TestCases.Create = {};
Nitrate.TestCases.Edit = {};
Nitrate.TestCases.Clone = {};

Nitrate.TestCases.AdvanceList.on_load = function() {
  bind_category_selector_to_product(true, true, jQ('#id_product')[0], jQ('#id_category')[0]);
  bind_component_selector_to_product(true, true, jQ('#id_product')[0], jQ('#id_component')[0]);

  if (jQ('#id_checkbox_all_case').length) {
    jQ('#id_checkbox_all_case').on('click', function(e) {
      clickedSelectAll(this, jQ(this).closest('form')[0], 'case');
      if (this.checked) {
        jQ('#case_advance_printable').attr('disabled', false);
      } else {
        jQ('#case_advance_printable').attr('disabled', true);
      }
    });
  }

  jQ('#id_blind_all_link').on('click', function(e) {
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

  jQ('.expandable').on('click', function (e) {
    let c = jQ(this).parent()[0]; // Container
    let c_container = jQ(c).next()[0]; // Content Containers
    let case_id = jQ(c).find('input[name="case"]')[0].value;

    toggleTestCasePane({ case_id: case_id, casePaneContainer: jQ(c_container) });
    toggleExpandArrow({ caseRowContainer: jQ(c), expandPaneContainer: jQ(c_container) });
  });

  jQ("#testcases_table tbody tr input[type=checkbox][name=case]").on('click', function() {
    if (jQ('input[type=checkbox][name=case]:checked').length) {
      jQ("#case_advance_printable").attr('disabled', false);
    } else {
      jQ("#case_advance_printable").attr('disabled', true);
    }
  });

  if (window.location.hash === '#expandall') {
    blinddownAllCases();
  }

  let listParams = Nitrate.TestCases.List.Param;
  jQ('#case_advance_printable').on('click', function() {
    postToURL(listParams.case_printable, Nitrate.Utils.formSerialize(this.form));
  });
  jQ('#export_selected_cases').on('click', function() {
    postToURL(listParams.case_export, Nitrate.Utils.formSerialize(this.form));
  });
};

Nitrate.TestCases.List.on_load = function() {
  bind_category_selector_to_product(true, true, jQ('#id_product')[0], jQ('#id_category')[0]);
  bind_component_selector_to_product(true, true, jQ('#id_product')[0], jQ('#id_component')[0]);
  if (jQ('#id_checkbox_all_case')[0]) {
    jQ('#id_checkbox_all_case').on('click', function(e) {
      clickedSelectAll(this, jQ(this).closest('table')[0], 'case');
      if (this.checked) {
        jQ('#case_list_printable').attr('disabled', false);
      } else {
        jQ('#case_list_printable').attr('disabled', true);
      }
    });
  }

  jQ('#id_blind_all_link').on('click', function(e) {
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
        this.title = "Collapse all cases";
        blinddownAllCases(element);
      } else {
        this.title = "Expand all cases";
        blindupAllCases(element);
      }
    }
  });

  if (window.location.hash === '#expandall') {
    blinddownAllCases();
  }

  jQ('#testcases_table').dataTable({
    "iDisplayLength": 20,
    "sPaginationType": "full_numbers",
    "bFilter": false,
    "bLengthChange": false,
    "aaSorting": [[ 2, "desc" ]],
    "bProcessing": true,
    "bServerSide": true,
    "sAjaxSource": "/cases/ajax/"+this.window.location.search,
    "aoColumns": [
      {"bSortable": false,"sClass": "expandable" },
      {"bSortable": false },
      {"sType": "html","sClass": "expandable"},
      {"sType": "html","sClass": "expandable"},
      {"sType": "html","sClass": "expandable"},
      {"sClass": "expandable"},
      {"sClass": "expandable"},
      {"sClass": "expandable"},
      {"sClass": "expandable"},
      {"sClass": "expandable"},
      {"sClass": "expandable"}
    ]
  });
  jQ("#testcases_table tbody tr td.expandable").on("click", function() {
    let tr = jQ(this).parent();
    let caseRowContainer = tr;
    let case_id = caseRowContainer.find('input[name="case"]').attr('value');
    let detail_td = '<tr class="case_content hide" style="display: none;"><td colspan="11">' +
      '<div id="id_loading_' + case_id + '" class="ajax_loading"></div></td></tr>';
    if (!caseRowContainer.next().hasClass('hide')) {
      caseRowContainer.after(detail_td);
    }

    toggleTestCasePane({ case_id: case_id, casePaneContainer: tr.next() });
    toggleExpandArrow({ caseRowContainer: tr, expandPaneContainer: tr.next() });
  });

  jQ("#testcases_table tbody tr input[type=checkbox][name=case]").on("click", function() {
    if (jQ("input[type=checkbox][name=case]:checked").length) {
      jQ("#case_list_printable").attr('disabled', false);
    } else {
      jQ("#case_list_printable").attr('disabled', true);
    }
  });

  let listParams = Nitrate.TestCases.List.Param;
  jQ('#case_list_printable').on('click', function() {
    postToURL(listParams.case_printable, Nitrate.Utils.formSerialize(this.form));
  });
  jQ('#export_selected_cases').on('click', function() {
    postToURL(listParams.case_export, Nitrate.Utils.formSerialize(this.form));
  });
};

Nitrate.TestCases.Details.on_load = function() {
  let case_id = Nitrate.TestCases.Instance.pk;

  constructTagZone(jQ('#tag')[0], { 'case': case_id });

  jQ('li.tab a').on('click', function(e) {
    jQ('div.tab_list').hide();
    jQ('li.tab').removeClass('tab_focus');
    jQ(this).parent().addClass('tab_focus');
    jQ('#' + this.title).show();
  });

  if (window.location.hash) {
    fireEvent(jQ('a[href=\"' + window.location.hash + '\"]')[0], 'click');
  }

  jQ('#id_add_component').on('click', function(e) {
    if (this.disabled) {
      return false;
    }

    renderComponentForm(
      getDialog(),
      {
        'case': Nitrate.TestCases.Instance.pk,
        'product': Nitrate.TestCases.Instance.product_id,
        'category': Nitrate.TestCases.Instance.category_id
      },
      function (e) {
        e.stopPropagation();
        e.preventDefault();

        let params = Nitrate.Utils.formSerialize(this);
        params['case'] = Nitrate.TestCases.Instance.pk;

        jQ.ajax('/cases/add-component/', {
          type: 'POST',
          dataType: 'json',
          data: params,
          traditional: true,
          success: function (data, textStatus, xhr) {
            window.location.reload();
          },
          error: function (xhr, textStatus, errorThrown) {
            json_failure(xhr);
          }
        });
      }
    );
  });

  jQ('#id_remove_component').on('click', function() {
    if (! window.confirm(default_messages.confirm.remove_case_component)) {
      return false;
    }

    let params = Nitrate.Utils.formSerialize(this.form);
    if (!params.component) {
      return false;
    }

    jQ.ajax('/cases/remove-component/', {
      type: 'POST',
      dataType: 'json',
      data: {
        'case': Nitrate.TestCases.Instance.pk,
        'o_component': params.component
      },
      traditional: true,
      success: function () {
        window.location.reload();
      },
      statusCode: {
        400: function (xhr) {
          json_failure(xhr);
        },
        403: function () {
          window.alert('You are not allowed to remove component from case.');
        }
      }
    });
  });

  jQ('.link_remove_component').on('click', function(e) {
    if (! window.confirm(default_messages.confirm.remove_case_component)) {
      return false;
    }

    jQ.ajax('/cases/remove-component/', {
      type: 'POST',
      dataType: 'json',
      data: {
        'case': Nitrate.TestCases.Instance.pk,
        'o_component': jQ('input[name="component"]')[jQ('.link_remove_component').index(this)].value
      },
      traditional: true,
      success: function () {
        window.location.reload();
      },
      statusCode: {
        400: function (xhr) {
          json_failure(xhr);
        },
        403: function () {
          window.alert('You are not allowed to add issue to case.');
        }
      }
    });
  });

  bindSelectAllCheckbox(jQ('#id_checkbox_all_components')[0], jQ('#id_form_case_component')[0], 'component');

  jQ('.plan_expandable').on('click', function (e) {
    let c = jQ(this).parent();
    toggleCaseRunsByPlan(
      {
        'type' : 'case_run_list',
        'container': c[0],
        'c_container': c.next()[0],
        'case_id': c.find('input').first().val(),
        'case_run_plan_id': c[0].id
      },
      function (e) {
        jQ('#table_case_runs_by_plan .expandable').on('click', function (e) {
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

  jQ('#btn_edit,#btn_clone').on('click', function() {
    window.location.href = jQ(this).data('link');
  });

  jQ('.js-del-button').on('click', function(event) {
    let params = jQ(event.target).data('params');
    deleConfirm(params.attachmentId, params.source, params.sourceId);
  });

  jQ('.js-remove-issue').on('click', function(event) {
    let params = jQ(event.target).data('params');
    removeCaseIssue(params.issueKey, params.caseId, params.caseRunId);
  });

  jQ('.js-add-issue').on('click', function(event) {
    addCaseIssue(jQ('#id_case_issue_form')[0]);
  });

  jQ('#issue_key').on('keydown', function(event) {
    addCaseIssueViaEnterKey(jQ('#id_case_issue_form')[0], event);
  });
};

/*
 * Resize all editors within the webpage after they are rendered.
 * This is used to avoid a bug of TinyMCE in Firefox 11.
 */
function resize_tinymce_editors() {
  jQ('.mceEditor .mceIframeContainer iframe').each(function(item) {
    let elem = jQ(this);
    elem.height(elem.height() + 1);
  });
}

Nitrate.TestCases.Create.on_load = function() {
  SelectFilter.init("id_component", "component", 0, "/static/admin/");
  //init category and components
  getCategoriesByProductId(false, jQ('#id_product')[0], jQ('#id_category')[0]);
  let from = 'id_component_from';
  let to = 'id_component_to';
  let from_field = jQ('#' + from)[0];
  let to_field = jQ('#' + to)[0];
  jQ(to_field).html('');
  getComponentsByProductId(false, jQ('#id_product')[0], from_field, function() {
    SelectBox.cache[from] = [];
    SelectBox.cache[to] = [];
    for (let i = 0; (node = from_field.options[i]); i++) {
      SelectBox.cache[from].push({value: node.value, text: node.text, displayed: 1});
    }
  });
  // bind change on product to update component and category
  jQ('#id_product').change(function () {
    let from = 'id_component_from';
    let to = 'id_component_to';
    let from_field = jQ('#' + from)[0];
    let to_field = jQ('#' + to)[0];
    jQ(to_field).html('');
    getComponentsByProductId(false, jQ('#id_product')[0], from_field, function() {
      SelectBox.cache[from] = [];
      SelectBox.cache[to] = [];
      for (let i = 0; (node = from_field.options[i]); i++) {
        SelectBox.cache[from].push({value: node.value, text: node.text, displayed: 1});
      }
    });
    getCategoriesByProductId(false, jQ('#id_product')[0], jQ('#id_category')[0]);
  });

  resize_tinymce_editors();

  jQ('.js-case-cancel').on('click', function() {
    window.history.go(-1);
  });
  if (jQ('.js-plan-cancel').length) {
    jQ('.js-plan-cancel').on('click', function() {
      window.location.href = jQ(this).data('param');
    });
  }
};

Nitrate.TestCases.Edit.on_load = function() {
  bind_category_selector_to_product(false, false, jQ('#id_product')[0], jQ('#id_category')[0]);
  resize_tinymce_editors();

  jQ('.js-back-button').on('click', function() {
    window.history.go(-1);
  });
};

Nitrate.TestCases.Clone.on_load = function() {
  bind_version_selector_to_product(true);

  jQ('#id_form_search_plan').on('submit', function(e) {
    e.stopPropagation();
    e.preventDefault();

    let container = jQ('#id_plan_container');
    container.show();

    jQ.ajax({
      'url': '/plans/',
      'type': 'GET',
      'data': jQ(this).serialize(),
      'success': function (data, textStatus, jqXHR) {
        container.html(data);
      }
    });
  });

  jQ('#id_use_filterplan').on('click', function(e) {
    jQ('#id_form_search_plan :input').attr('disabled', false);
    jQ('#id_plan_id').val('');
    jQ('#id_plan_id').attr('name', '');
    jQ('#id_copy_case').attr('checked', true);
  });

  if (jQ('#id_use_sameplan').length) {
    jQ('#id_use_sameplan').on('click', function(e) {
      jQ('#id_form_search_plan :input').attr('disabled', true);
      jQ('#id_plan_id').val(jQ('#value_plan_id').val());
      jQ('#id_plan_id').attr('name', 'plan');
      jQ('#id_plan_container').html('<div class="ajax_loading"></div>').hide();
      jQ('#id_copy_case').attr('checked', false);
    });
  }

  jQ('.js-cancel-button').on('click', function() {
    window.history.go('-1');
  });

};


/*
 * Used for expanding test case in test plan page specifically
 *
 * Arguments:
 * options.caseRowContainer: a jQuery object referring to the container of the
 *                           test case that is being expanded to show more
 *                           information.
 * options.expandPaneContainer: a jQuery object referring to the container of
 *                              the expanded pane showing test case detail
 *                              information.
 */
function toggleExpandArrow(options) {
  let container = options.caseRowContainer;
  let content_container = options.expandPaneContainer;
  let blind_icon = container.find('img.blind_icon');
  if (content_container.css('display') === 'none') {
    blind_icon.removeClass('collapse').addClass('expand').attr('src', '/static/images/t1.gif');
  } else {
    blind_icon.removeClass('expand').addClass('collapse').attr('src', '/static/images/t2.gif');
  }
}


/*
 * Toggle simple caserun pane in Case Runs tab in case page.
 */
function toggleSimpleCaseRunPane(options) {
  options.expandPaneContainer.toggle();

  if (options.caserunRowContainer.next().find('.ajax_loading').length) {
    jQ.get(
      '/case/' + options.caseId + '/caserun-simple-pane/',
      {case_run_id: options.caserunId},
      function(data, textStatus) {
        options.expandPaneContainer.html(data);
      },
      'html');
  }

  toggleExpandArrow({
    caseRowContainer: options.caserunRowContainer,
    expandPaneContainer: options.expandPaneContainer
  });
}

function toggleTestCaseContents(template_type, container, content_container, object_pk, case_text_version, case_run_id, callback) {
  // TODO: should container and content_container be in string type?

  if (typeof container === 'string') {
    container = jQ('#' + container)[0];
  }

  if(typeof content_container === 'string') {
    content_container = jQ('#' + content_container)[0];
  }

  jQ(content_container).toggle();

  if (jQ('#id_loading_' + object_pk).length) {
    jQ.ajax({
      'url': Nitrate.http.URLConf.reverse({ name: 'case_details', arguments: {id: object_pk} }),
      'data': {
        template_type: template_type,
        case_text_version: case_text_version,
        case_run_id: case_run_id
      },
      'success': function (data, textStatus, jqXHR) {
        jQ(content_container).html(data);
      },
      'error': function (jqXHR, textStatus, errorThrown) {
        html_failure();
      },
      'complete': function (jqXHR, textStatus) {
        callback(jqXHR);
      }
    });
  }

  toggleExpandArrow({ caseRowContainer: jQ(container), expandPaneContainer: jQ(content_container) });
}

function changeTestCaseStatus(plan_id, selector, case_id, be_confirmed, was_confirmed) {
  jQ.ajax('/ajax/update/case-status/', {
    type: 'POST',
    dataType: 'json',
    data: {
      'from_plan': plan_id,
      'case': case_id,
      'target_field': 'case_status',
      'new_value': selector.value,
    },
    success: function(data) {
      let case_status = '';
      for (let i = 0; (node = selector.options[i]); i++) {
        if (node.selected) {
          case_status = node.innerHTML;
        }
      }

      // container should be got before selector is hidden.
      let curCasesContainer = jQ(selector).parents('.tab_list');

      let label = jQ(selector).prev()[0];
      jQ(label).html(case_status).show();
      jQ(selector).hide();

      if (be_confirmed || was_confirmed) {
        jQ('#run_case_count').text(data.run_case_count);
        jQ('#case_count').text(data.case_count);
        jQ('#review_case_count').text(data.review_case_count);
        jQ('#' + case_id).next().remove();
        jQ('#' + case_id).remove();

        // We have to reload the other side of cases to reflect the status
        // change. This MUST be done before selector is hided.
        Nitrate.TestPlans.Details.reopenTabHelper(curCasesContainer);
      }
    },
    statusCode: {
      400: function (xhr) {
        json_failure(xhr);
      },
      403: function () {
        window.alert('You are not allowed to add issue to case.');
      }
    }
  });
}

function toggleAllCheckBoxes(element, container, name) {
  if (element.checked) {
    jQ('#' + container).parent().find('input[name="' + name + '"]').not(':disabled').attr('checked', true);
  } else {
    jQ('#' + container).parent().find('input[name="'+ name + '"]').not(':disabled').attr('checked', false);
  }
}

function toggleAllCases(element) {
  //If and only if both case length is 0, remove the lock.
  if (jQ('div[id^="id_loading_"].normal_cases').length === 0 && jQ('div[id^="id_loading_"].review_cases').length === 0){
    jQ(element).removeClass('locked');
  }

  if (jQ(element).is('.locked')) {
    return false;
  } else {
    jQ(element).addClass('locked');
    if (jQ(element).is('.collapse-all')) {
      element.title = "Collapse all cases";
      blinddownAllCases(element);
    } else {
      element.title = "Expand all cases";
      blindupAllCases(element);
    }
  }
}

function blinddownAllCases(element) {
  jQ('img.expand').each(function(e) {
    fireEvent(this, 'click');
  });
  if (element) {
    jQ(element)
      .removeClass('collapse-all').addClass('expand-all')
      .attr('src', '/static/images/t2.gif');
  }
}

function blindupAllCases(element) {
  jQ('.collapse').each(function(e) {
    fireEvent(this, 'click');
  });

  if (element) {
    jQ(element)
      .removeClass('expand-all').addClass('collapse-all')
      .attr('src', '/static/images/t1.gif');
  }
}

// Deprecated. Remove when it's unusable any more.
function changeCaseOrder(parameters, callback) {
  let nsk = '';
  if (parameters.hasOwnProperty('sortkey')) {
    nsk = window.prompt('Enter your new order number', parameters.sortkey);   // New sort key
    if (parseInt(nsk) === parseInt(parameters.sortkey)) {
      window.alert('Nothing changed');
      return false;
    }
  } else {
    nsk = window.prompt('Enter your new order number');
  }

  if (!nsk) {
    return false;
  }

  if (isNaN(nsk)) {
    window.alert('The value must be an integer number and limit between 0 to 32300.');
    return false;
  }

  nsk = parseInt(nsk);

  if (nsk > 32300 || nsk < 0) {
    window.alert('The value must be a number and limit between 0 to 32300.');
    return false;
  }

  updateObject(
    'testcases.testcaseplan', parameters.testcaseplan,
    'sortkey', 'nsk', 'int', callback
  );
}

function changeCaseOrder2(parameters, callback) {
  let nsk = '';
  if (parameters.hasOwnProperty('sortkey')) {
    nsk = window.prompt('Enter your new order number', parameters.sortkey);   // New sort key
    if (parseInt(nsk) === parseInt(parameters.sortkey)) {
      window.alert('Nothing changed');
      return false;
    }
  } else {
    nsk = window.prompt('Enter your new order number');
  }

  if (!nsk) {
    return false;
  }

  if (isNaN(nsk)) {
    window.alert('The value must be a number and limit between 0 to 32300.');
    return false;
  }

  nsk = parseInt(nsk);

  if (nsk > 32300 || nsk < 0) {
    window.alert('The value must be an integer number and limit between 0 to 32300.');
    return false;
  }

  parameters.target_field = 'sortkey';
  parameters.new_value = nsk;

  jQ.ajax('/ajax/update/cases-sortkey/', {
    type: 'POST',
    dataType: 'json',
    data: parameters,
    traditional: true,
    success: function () {
      callback();
    },
    error: function (xhr) {
      json_failure(xhr);
    }
  });
}

function addCaseIssue(form) {
  let addIssueForm = jQ(form);
  let issueKey = addIssueForm.find('input#issue_key').val().trim();

  let selectedIssueTrackerOption = addIssueForm.find('option:selected');
  let issueKeyRegex = selectedIssueTrackerOption.data('issue-key-regex');
  if (! RegExp(issueKeyRegex).test(issueKey)) {
    alert('Issue key is malformat.');
    return;
  }

  if (!issueKey.length) {
    // No bug ID input, no any response is required
    return false;
  }

  jQ.ajax(form.action, {
    // URL has the case ID, hence no need to pass case ID again through request
    // data.
    data: {
      handle: 'add',
      issue_key: issueKey,
      tracker: parseInt(selectedIssueTrackerOption.val())
    },
    dataType: 'json',
    success: function (responseJSON, textStatus, jqXHR) {
      jQ('#issues').html(responseJSON.html);
    },
    complete: function (jqXHR, textStatus) {
      if (textStatus === 'error') {
        return;
      }

      jQ('.js-add-issue').on('click', function(event) {
        addCaseIssue(jQ('#id_case_issue_form')[0]);
      });
      jQ('.js-remove-issue').on('click', function(event) {
        let params = jQ(event.target).data('params');
        removeCaseIssue(params.issueKey, params.caseId, params.caseRunId);
      });
      if (jQ('#response').length) {
        window.alert(jQ('#response').html());
        return false;
      }

      jQ('#case_issues_count').text(jQ('table#issues').attr('count'));
    },
    statusCode: {
      400: function (xhr) {
        json_failure(xhr);
      },
      403: function () {
        window.alert('You are not allowed to add issue to case.');
      }
    }
  });
}

function removeCaseIssue(issue_key, case_id, case_run_id) {
  if(!window.confirm('Are you sure to remove issue $id?'.replace('$id', issue_key))) {
    return false;
  }

  jQ.ajax({
    'url': '/case/' + case_id + '/issue/',
    'type': 'GET',
    'data': {
      'handle': 'remove',
      'issue_key': issue_key,
      'case_run': case_run_id
    },
    'success': function (data) {
      jQ('#issues').html(data.html);
    },
    'complete': function (jqXHR, textStatus) {
      if (textStatus === 'error') {
        return;
      }

      jQ('.js-remove-issue').on('click', function(event) {
        let params = jQ(event.target).data('params');
        removeCaseIssue(params.issueKey, params.caseId, params.caseRunId);
      });
      jQ('.js-add-issue').on('click', function(event) {
        addCaseIssue(jQ('#id_case_issue_form')[0]);
      });

      jQ('#case_issues_count').text(jQ('table#issues').attr('count'));
    },
    statusCode: {
      400: function (xhr) {
        json_failure(xhr);
      },
      403: function () {
        window.alert('You are not allowed to add issue to case.');
      }
    }
  });
}


/**
 * Handle triggered by click event of Remove button to remove a plan from a
 * case' plans table. This is bound to specific element in the template directly.
 * @param {number} caseId
 * @param {HTMLButtonElement} button - the element this handler is bound to.
 */
function removePlanFromPlansTableHandler(caseId, button) {
  if (! window.confirm('Are you sure to remove the case from this plan?')) {
    return;
  }
  jQ.ajax('/case/' + caseId + '/plans/remove/', {
    type: 'POST',
    dataType: 'json',
    data: {plan: parseInt(jQ(button).data('planid'))},
    success: function (data) {
      jQ('#plan').html(data.html);
      jQ('#plan_count').text(jQ('table#testplans_table').attr('count'));
    },
    statusCode: {
      400: function (xhr) {
        json_failure(xhr);
      },
      403: function () {
        window.alert('You are not allowed to do this operation.');
      }
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
    window.alert(default_messages.alert.no_plan_specified);
    return;
  }

  let casePlansUrl = '/case/' + caseId + '/plans/';

  previewPlan({pk__in: planIds}, casePlansUrl, function (e) {
    e.stopPropagation();
    e.preventDefault();

    let plan_ids = Nitrate.Utils.formSerialize(this).plan_id;
    if (!plan_ids) {
      window.alert(default_messages.alert.no_plan_specified);
      return false;
    }

    clearDialog();

    jQ.ajax(casePlansUrl + 'add/', {
      type: 'POST',
      dataType: 'json',
      data: {plan: plan_ids},
      traditional: true,
      success: function (data) {
        jQ('#plan').html(data.html);
        jQ('#plan_count').text(jQ('table#testplans_table').attr('count'));
      },
      statusCode: {
        400: function (xhr) {
          json_failure(xhr);
        },
        403: function () {
          window.alert('You are not allowed to do this operation.');
        }
      }
    });
  });
}

function renderTagForm(container, parameters, form_observe) {
  let d = jQ('<div>');
  if (!container) {
    container = getDialog();
  }
  jQ(container).show();

  jQ.ajax({
    'url': Nitrate.http.URLConf.reverse({ name: 'cases_tag' }),
    'type': 'POST',
    'data': parameters,
    'traditional': true,
    'success': function (data, textStatus, jqXHR) {
      d.html(data);
    },
    'error': function (jqXHR, textStatus, errorThrown) {
      html_failure();
    },
    'complete': function() {
      let h = jQ('<input>', {'type': 'hidden', 'name': 'a', 'value': 'remove'});
      let a = jQ('<input>', {'type': 'submit', 'value': 'Remove'});
      let c = jQ('<label>');
      c.append(h);
      c.append(a);
      a.on('click', function(e) { h.val('remove'); });
      jQ(container).html(constructForm(
        d.html(),
        Nitrate.http.URLConf.reverse({name: 'cases_tag'}),
        form_observe,
        'Press "Ctrl" to select multiple default component',
        c[0])
      );
      bind_component_selector_to_product(false, false, jQ('#id_product')[0], jQ('#id_o_component')[0]);
    }
  });
}

function renderComponentForm(container, parameters, form_observe) {
  let d = jQ('<div>');
  if (!container) {
    container = getDialog();
  }
  jQ(container).show();

  jQ.ajax({
    'url': '/cases/get-component-form/',
    'type': 'POST',
    'data': parameters,
    'success': function (data, textStatus, jqXHR) {
      d.html(data);
    },
    'error': function (jqXHR, textStatus, errorThrown) {
      html_failure();
    },
    'complete': function() {
      let a = jQ('<input>', {'type': 'submit', 'value': 'Add'});
      let c = jQ('<label>');
      c.append(a);
      jQ(container).html(
        constructForm(
          d.html(),
          '/cases/add-component/',
          form_observe,
          'Press "Ctrl" to select multiple default component',
          c[0])
      );
      bind_component_selector_to_product(
        false, false, jQ('#id_product')[0], jQ('#id_o_component')[0]);
    }
  });
}


function renderCategoryForm(container, parameters, form_observe) {
  let d = jQ('<div>');
  if (!container) {
    container = getDialog();
  }
  jQ(container).show();

  jQ.ajax('/cases/category/', {
    type: 'POST',
    data: parameters,
    success: function (data) {
      d.html(data);
    },
    error: function () {
      html_failure();
    },
    complete: function() {
      let h = jQ('<input>', {'type': 'hidden', 'name': 'a', 'value': 'add'});
      let a = jQ('<input>', {'type': 'submit', 'value': 'Select'});
      let c = jQ('<label>');
      c.append(h);
      c.append(a);
      a.on('click', function(e) { h.val('update'); });
      jQ(container).html(
        constructForm(d.html(), '/cases/category/', form_observe, 'Select Category', c[0])
      );
      bind_category_selector_to_product(
        false, false, jQ('#id_product')[0], jQ('#id_o_category')[0]);
    }
  });
}

// FIXME: abstract this function
function updateCaseTag(url, parameters, callback) {
  jQ.ajax({
    'url': url,
    'type': 'POST',
    'dataType': 'json',
    'data': parameters,
    'success': function (data, textStatus, jqXHR) {
      callback(data);
    },
    'error': function (jqXHR, textStatus, errorThrown) {
      json_failure(jqXHR);
    }
  });
}

function constructCaseAutomatedForm(container, options, callback) {
  jQ(container).html(getAjaxLoading());
  jQ(container).show();
  let d = jQ('<div>', { 'class': 'automated_form' })[0];

  getForm(d, 'testcases.CaseAutomatedForm', {}, function (jqXHR) {
    let returntext = jqXHR.responseText;

    jQ(container).html(
      constructForm(returntext, '/cases/automated/', function (e) {
        e.stopPropagation();
        e.preventDefault();

        if (!jQ(this).find('input[type="checkbox"]:checked').length) {
          window.alert('Nothing selected');
          return false;
        }

        let params = serializeFormData({
          form: this,
          zoneContainer: options.zoneContainer,
          selectedCaseIDs: options.selectedCaseIDs,
        });
        /*
         * Have to add this. The form generated before does not contain a
         * default value `change'. In fact, the field a onust contain the
         * only value `change', here.
         */
        params = params.replace(/a=\w*/, 'a=change');
        jQ.ajax(Nitrate.http.URLConf.reverse({ name: 'cases_automated' }), {
          type: 'POST',
          dataType: 'json',
          data: params,
          success: function () {
            callback();
          },
          statusCode: {
            400: function () {
              window.alert('You are not allowed to change test case automation attribute.');
            },
            403: function (xhr) {
              window.alert(JSON.parse(xhr.responseText).message);
            }
          }
        });
      })
    );
  });
}

/**
 * Collect selected case IDs from a given container HTML element.
 * @param {HTMLElement} container - could be any container like HTML element from where to find out
 *                                  checked inputs with type checkbox and name case.
 * @returns {string[]} a list of selected case IDs without parsing to integer value.
 */
function getSelectedCaseIDs(container) {
  return jQ(container).find('input[name="case"]:checked').map(function () {
    return jQ(this).val();
  }).get();
}

function toggleDiv(link, divId) {
  link = jQ(link);
  let div = jQ('#' + divId);
  let show = 'Show All';
  let hide = 'Hide All';
  div.toggle();
  let text = link.html();
  if (text !== show) {
    link.html(show);
  } else {
    link.html(hide);
  }
}

function addCaseIssueViaEnterKey(element, e) {
  if (e.keyCode === 13) {
    addCaseIssue(element);
  }
}

function toggleCaseRunsByPlan(params, callback) {
  let container = params.container;

  if (typeof container === 'string') {
    container = jQ('#' + container);
  } else {
    container = jQ(container);
  }

  let content_container = params.c_container;

  if(typeof content_container === 'string') {
    content_container = jQ('#' + content_container);
  } else {
    content_container = jQ(content_container);
  }

  content_container.toggle();

  if (jQ('#id_loading_' + params.case_run_plan_id).length) {
    jQ.ajax({
      'url': '/case/' + params.case_id + '/caserun-list-pane/',
      'type': 'GET',
      'data': {plan_id: params.case_run_plan_id},
      'success': function (data, textStatus, jqXHR) {
        content_container.html(data);
      },
      'error': function (jqXHR, textStatus, errorThrown) {
        html_failure();
      },
      'complete': function() {
        callback();
      }
    });
  }

  let blind_icon = container.find('img').first();
  if (content_container.is(':hidden')) {
    blind_icon.removeClass('collapse').addClass('expand').attr('src', '/static/images/t1.gif');
  } else {
    blind_icon.removeClass('expand').addClass('collapse').attr('src', '/static/images/t2.gif');
  }
}
