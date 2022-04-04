/* global CaseRunDetailExpansion */
/* global caseDetailExpansionHandler */

Nitrate.TestRuns = {};
Nitrate.TestRuns.Search = {};
Nitrate.TestRuns.List = {};
Nitrate.TestRuns.Details = {};
Nitrate.TestRuns.New = {};
Nitrate.TestRuns.Edit = {};
Nitrate.TestRuns.Execute = {};
Nitrate.TestRuns.Clone = {};
Nitrate.TestRuns.ChooseRuns = {};
Nitrate.TestRuns.AssignCase = {};
Nitrate.TestRuns.AdvancedSearch = {};


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

/**
 * Remove a case from test run new page.
 *
 * @param {string} item - the HTML id of a container element containing the case to be removed.
 * @param {number} caseEstimatedTime - the case' estimated time.
 */
function removeItem(item, caseEstimatedTime) {
  let trEstimatedTime = jQ('#estimated_time').data('time');
  let remainEstimatedTime = trEstimatedTime - caseEstimatedTime;
  let secondValue = remainEstimatedTime % 60;
  let minute = parseInt(remainEstimatedTime / 60);
  let minuteValue = minute % 60;
  let hour = parseInt(minute / 60);
  let hourValue = hour % 24;
  let dayValue = parseInt(hour / 24);

  let remainEstimatedTimeValue = dayValue ? dayValue + 'd' : '';
  remainEstimatedTimeValue += hourValue ? hourValue + 'h' : '';
  remainEstimatedTimeValue += minuteValue ? minuteValue + 'm' : '';
  remainEstimatedTimeValue += secondValue ? secondValue + 's' : '';

  if (!remainEstimatedTimeValue.length) {
    remainEstimatedTimeValue = '0m';
  }

  jQ('#estimated_time').data('time', remainEstimatedTime);
  // TODO: can't set value through jquery setAttribute.
  document.getElementById('id_estimated_time').value = remainEstimatedTimeValue;
  jQ('#' + item).remove();
}


/**
 * Initialize the test runs search result table and associated action buttons.
 *
 * @param {string} searchEndpoint - the endpoint to search test runs.
 */
Nitrate.TestRuns.Search.initializeSearchResult = function (searchEndpoint) {
  let runsSearchResultTableSettings = Object.assign({}, Nitrate.DataTable.commonSettings, {
    aaSorting: [[1, 'desc']],
    sAjaxSource: searchEndpoint + window.location.search,

    iDeferLoading: this.numberOfRuns,

    aoColumns: [
      {'bSortable': false},       // Select checker
      {'sType': 'numeric'},       // ID
      {'sType': 'html'},          // Summary
      {'sType': 'html'},          // Manager
      {'sType': 'html'},          // Default Tester
      null,                       // Product
      null,                       // Product Version
      null,                       // Environment
      {'sType': 'numeric'},       // Cases
      {'sType': 'html'},          // Status
      {'bSortable': false}        // Completed progress
    ],

    oLanguage: {
      sEmptyTable: 'No run was found.'
    },

    fnInitComplete: function () {
      jQ('.js-clone-testruns').on('click', function () {
        let params = Nitrate.Utils.formSerialize(this.form);
        postToURL(this.dataset.actionUrl, params, 'get');
      });
    },

    fnDrawCallback: function () {
      jQ('#testruns_table tbody tr td:nth-child(1)').shiftcheckbox({
        checkboxSelector: ':checkbox',
        selectAll: '#testruns_table .js-select-all'
      });

      jQ('#testruns_table :checkbox').on('change', function () {
        jQ('.js-clone-testruns').prop(
          'disabled', jQ('#testruns_table tbody :checkbox:checked').length === 0
        );
      });
    },

    fnInfoCallback: function (oSettings, iStart, iEnd, iMax, iTotal, sPre) {
      return 'Showing ' + (iEnd - iStart + 1) + ' of ' + iTotal + ' runs';
    }

  });

  jQ('#testruns_table').dataTable(runsSearchResultTableSettings);
};

Nitrate.TestRuns.AdvancedSearch.on_load = function () {
  Nitrate.TestRuns.Search.initializeSearchResult('/advance-search/');
};

Nitrate.TestRuns.List.on_load = function () {
  registerProductAssociatedObjectUpdaters(
    document.getElementById('id_product'),
    false,
    [
      {
        func: getBuildsByProductId,
        targetElement: document.getElementById('id_build'),
        addBlankOption: true,
      },
      {
        func: getVersionsByProductId,
        targetElement: document.getElementById('id_product_version'),
        addBlankOption: true,
      }
    ]
  );

  //Nitrate.Utils.enableShiftSelectOnCheckbox('run_selector');

  if (jQ('#id_people_type').length) {
    jQ('#id_search_people').prop('name', jQ('#id_people_type').val());
    jQ('#id_people_type').on('change', function () {
      jQ('#id_search_people').prop('name', jQ('#id_people_type').val());
    });
  }

  if (jQ('#run_column_add').length) {
    jQ('#run_column_add').on('change', function () {
      switch(this.value) {
        case 'col_plan':
          jQ('#col_plan_head').show();
          jQ('.col_plan_content').show();
          jQ('#col_plan_option').hide();
          break;
      }
    });
  }

  Nitrate.TestRuns.Search.initializeSearchResult('/runs/');
};


/*
 * Show the number of case run's issues in run statistics after adding issue to
 * a case run.
 *
 * Args:
 * newIssuesCount: the number of case run's issues.
 * runId: test run ID to construct report URL if there is issue added.
 */
function showTheNumberOfCaseRunIssues(newIssuesCount, runId) {
  if (parseInt(newIssuesCount) === 0) {
    jQ('div#run-statistics')
      .find('span#total_run_issues_count')
      .html('No Issues');
  } else {
    // NOTE: Construct this HTML would be not good. Probably we could refresh
    //       the run statistics section with an AJAX call to server-side API.
    //       This could be also a good point for creating a reusable run
    //       statistics API for general use.
    let runReportUrl = '/run/' + runId + '/report/#issues';
    jQ('div#run-statistics')
      .find('span#total_run_issues_count')
      .html('<a title="Show All Issues" href=' + runReportUrl + '>Issues [' + newIssuesCount + ']</a>');
  }
}


/**
 * Update the number of a case run's issues.
 *
 * @param {jQuery} caseRunRow - the container containing case run.
 * @param {number} caseRunIssuesCount - the number of issues.
 */
function updateIssuesCountInCaseRunRow(caseRunRow, caseRunIssuesCount) {
  let caseRunIssuesCountSpan = jQ(caseRunRow).find('span[id$="_case_issues_count"]');
  caseRunIssuesCountSpan.text(caseRunIssuesCount.toString());
  if (caseRunIssuesCount > 0) {
    caseRunIssuesCountSpan.addClass('have_issue');
  } else {
    caseRunIssuesCountSpan.removeClass('have_issue');
  }
}


function AddIssueDialog() {
  this.dialog = jQ('#add-issue-dialog').dialog({
    autoOpen: false,
    resizable: false,
    modal: true,

    beforeClose: function () {
      // Whenever dialog is closed, previous input issue key should be cleared
      // in order to not confuse user when use next time.
      jQ(this).find('input:text').val('');
    },

    buttons: {
      Add: function () {
        let dialog = jQ(this);
        let selectedIssueTracker = dialog.find('select[id="issue_tracker_id"] option:selected');
        let issueTrackerID = selectedIssueTracker.val();
        let validateRegex = selectedIssueTracker.data('validate-regex');
        let issueInputSection = dialog.find('div#' + selectedIssueTracker.data('tab'));

        let issueKey = issueInputSection.find('input[name="issue_key"]').val();
        let optLinkExternalTracker = issueInputSection.find('input[name="link_external_tracker"]');
        let addIssueInfo = dialog.dialog('option', 'addIssueInfo');

        if (! new RegExp(validateRegex).test(issueKey)) {
          showModal('Issue key is malformated.');
          return;
        }

        let data = {
          'a': 'add',
          'issue_key': issueKey,
          'tracker': issueTrackerID,
          'case_run': addIssueInfo.caseRunIds
        };

        // If selected issue tracker has option "add case to issue's external
        // tracker", handle it. If no, just ignore it.
        if (optLinkExternalTracker.length > 0 && optLinkExternalTracker[0].checked) {
          data.link_external_tracker = 'on';
        }

        // FIXME: should be POST
        getRequest({
          url: '/run/' + addIssueInfo.runId + '/issues/',
          data: data,
          traditional: true,

          /**
           * After adding an issue successfully, number of issues inside the run page has to be updated
           * and reload case run detail content eventually.
           *
           * @param {object} data - server response data
           * @param {object} data.caserun_issues_count - a mapping from case run id to the number of issues it has.
           * @param {number} data.run_issues_count - the total number of issues of the test run.
           */
          success: function (data) {
            // After succeeding to add issue, we close the add dialog.
            dialog.dialog('close');

            let reloadPage = dialog.dialog('option', 'reloadPage');

            if (reloadPage) {
              window.location.reload();
            } else {
              let expansion = dialog.dialog('option', 'caseRunDetailExpansion')
                , caseRunId = addIssueInfo.caseRunIds[0]
                , caseRunIssuesCount = data.caserun_issues_count[caseRunId];
              updateIssuesCountInCaseRunRow(expansion.caseRunRow, caseRunIssuesCount);
              showTheNumberOfCaseRunIssues(data.run_issues_count, addIssueInfo.runId);
              expansion.showLoadingAnimation = true;
              expansion.expand();
            }
          },
        });
      },

      Cancel: function () {
        jQ(this).dialog('close');
      }
    }
  });
}

/**
 * Open the dialog
 *
 * @param {object} addIssueInfo - object containing data for adding an issue to case run(s).
 * @param {number[]} addIssueInfo.caseRunIds - an array of case run ids.
 * @param {number} addIssueInfo.runId - the run id.
 * @param {CaseRunDetailExpansion} [caseRunDetailExpansion] - the detail expansion used to reload
 *   detail content.
 */
AddIssueDialog.prototype.open = function (addIssueInfo, caseRunDetailExpansion) {
  if (addIssueInfo.caseRunIds === undefined || !Array.isArray(addIssueInfo.caseRunIds)) {
    throw new Error('addIssueInfo.caseRunIDs must be an array including case run IDs.');
  }

  let dialog = this.dialog;

  dialog.dialog('option', 'title', 'Add issue to case run');
  dialog.dialog('option', 'addIssueInfo', addIssueInfo);
  if (caseRunDetailExpansion) {
    dialog.dialog('option', 'caseRunDetailExpansion', caseRunDetailExpansion);
  }

  // Switch issue tracker tab
  dialog.find('#issue_tracker_id').change(function () {
    dialog.find('div[id^="issue-tracker-"]').filter(function () {
      return jQ(this).css('display') === 'block';
    }).toggle();

    let tabIdToShow = jQ('#issue_tracker_id option:selected').data('tab');
    dialog.find('#' + tabIdToShow).toggle();
  });

  dialog.dialog('open');
};

function AddEnvPropertyDialog(runId, envGroupId) {
  let that = this
    , valuesSelect = document.getElementById('propertyValuesSelect')
    , propertiesSelect = document.getElementById('propertiesSelect')
  ;

  this.runId = runId;
  this.envGroupId = envGroupId;

  jQ('#propertiesSelect').on('change', function () {
    let thisSelect = this;

    // Prevent from selecting another property before server side responses
    // current request to fill in the values SELECT.
    thisSelect.disabled = true;

    getRequest({
      url: '/management/getinfo/',
      data: {
        info_type: 'env_values',
        env_property_id: this.selectedOptions[0].value
      },
      errorMessage: 'Update values failed',
      success: function (data) {
        emptySelect(valuesSelect);

        if (data.length > 0) {
          setUpChoices(
            valuesSelect,
            data.map(function (o) {return [o.pk, o.fields.value];}),
            false,
          );
        }

        thisSelect.disabled = false;
      },
    });
  });

  this.dialog = jQ('#addEnvPropertyDialog').dialog({
    autoOpen: false,
    height: 260,
    width: 300,
    modal: true,
    buttons: {
      Add: function () {
        let valueId = valuesSelect.selectedOptions[0].value;
        addPropertyToEnv(that.runId, valueId);

        that.dialog.dialog('close');
        that.dialog.dialog('destroy');
      },
      Cancel: function () {
        that.dialog.dialog('close');
      }
    },
    open: function () {
      emptySelect(valuesSelect);
      emptySelect(propertiesSelect);

      // Fill in the properties SELECT

      getRequest({
        url: '/management/getinfo/',
        data: {info_type: 'env_properties', env_group_id: that.envGroupId},
        errorMessage: 'Update properties failed',
        success: function (data) {
          setUpChoices(
            propertiesSelect,
            data.map(function (o) {return [o.pk, o.fields.name];}),
            false
          );

          jQ(propertiesSelect).trigger('change');
        },
      });
    }
  });
}

AddEnvPropertyDialog.prototype.open = function () {
  this.dialog.dialog('open');
}

/**
 * Register event handlers for the elements inside case run detail row.
 *
 * @param {CaseRunDetailExpansion} expansion -
 */
Nitrate.TestRuns.Details.registerEventHandlersForCaseRunDetail = function (expansion) {
  let self = Nitrate.TestRuns.Details
    , caseRunDetailRow = expansion.detailRow
    ;

  // Observe the update case run status/comment form
  caseRunDetailRow.find('.update_form').off('submit').on('submit', function (e) {
    e.stopPropagation();
    e.preventDefault();
    console.log('Update status using expansion: ', expansion);
    updateCaseRunStatus(expansion, e.target);
  });

  caseRunDetailRow.find('.form_comment').off('submit').on('submit', function (e) {
    e.stopPropagation();
    e.preventDefault();
    if (!window.confirm(defaultMessages.confirm.remove_comment)) {
      return false;
    }
    removeComment(this, function () {
      updateCommentsCount(expansion.caseId, false);
      expansion.showLoadingAnimation = true;
      expansion.expand();
    });
  });

  caseRunDetailRow.find('.js-status-button').on('click', function () {
    this.form.comment.required = false;
    this.form.value.value = this.dataset.statusId;
  });

  caseRunDetailRow.find('.js-show-comments').on('click', function () {
    toggleDiv(this, this.dataset.commentsElementId);
  });

  caseRunDetailRow.find('.js-show-changelog').on('click', function () {
    toggleDiv(this, this.dataset.changelogsElementId);
  });

  caseRunDetailRow.find('.js-add-caserun-issue').on('click', function () {
    if (self.addIssueDialog === undefined) {
      self.addIssueDialog = new AddIssueDialog();
    }
    let dataset = this.dataset;
    let addIssueInfo = {
      runId: dataset.runId,
      caseRunIds: [dataset.caseRunId]
    };
    self.addIssueDialog.open(addIssueInfo, expansion);
  });

  caseRunDetailRow.find('.js-file-issue').on('click', function () {
    let dialogDiv = jQ('#select-tracker-dialog')
      , form = document.forms['issueTrackerSelectionForm']
      , fileDirectly = form.issueTrackers.options.length === 1;
    form.action = this.dataset.action;
    if (fileDirectly) {
      form.submit();
    } else {
      // Show the dialog to select an issue tracker
      let dialog = dialogDiv.dialog({
        autoOpen: false,
        resizable: false,
        modal: true,
        buttons: {
          Ok: function () {
            form.submit();
            jQ(this).dialog('destroy');
          },
          Cancel: function () {
            jQ(this).dialog('destroy');
          }
        }
      });
      dialog.dialog('open');
    }
  });

  caseRunDetailRow.find('.js-remove-caserun-issue').on('click', function () {
    let dataset = this.dataset;
    removeIssueFromCaseRuns(
      {
        runId: dataset.runId,
        caseId: dataset.caseId,
        caseRunIds: [dataset.caseRunId],
        issueKey: dataset.issueKey
      },
      function (data) {
        let caseRunIssuesCount = data.caserun_issues_count[dataset.caseRunId] || 0;
        updateIssuesCountInCaseRunRow(expansion.caseRunRow, caseRunIssuesCount);
        showTheNumberOfCaseRunIssues(data.run_issues_count, dataset.runId);
        expansion.showLoadingAnimation = true;
        expansion.expand();
      }
    );
  });

  caseRunDetailRow.find('.js-add-testlog').on('click', function () {
    let dialog = getAddLinkDialog();
    dialog.dialog('option', 'target_id', expansion.caseRunId);
    dialog.dialog('option', 'caseRunDetailExpansion', expansion);
    dialog.dialog('open');
  });

  caseRunDetailRow.find('.js-remove-testlog').on('click', function () {
    let self = this
      , linkId = window.parseInt(this.dataset.linkId)
      , url = '/linkref/remove/' + linkId + '/'
      ;
    postRequest({
      url: url,
      success: function () {
        let li = self.parentNode
          , ul = li.parentNode;
        ul.removeChild(li);
      }
    });
  });
};

function bindEnvPropertyHandlers() {
  jQ('.js-edit-property').on('click', function () {
    let dataset = this.dataset
      , formName = 'id_form_value_' + dataset.runEnvValueId
      , theEnvForm = document.forms[formName]
      , envPropertyId = theEnvForm.env_property_id.value
      ;

    document.getElementById(dataset.envValueElemId).style.display = 'none';
    document.getElementById(dataset.submitValueElemId).style.display = '';

    let selectValueElem = document.getElementById(dataset.selectValueElemId);
    selectValueElem.style.display = '';

    getRequest({
      url: dataset.actionUrl,
      data: {info_type: 'env_values', env_property_id: envPropertyId},
      errorMessage: 'Update values failed',
      success: function (data) {
        let currentValue = theEnvForm.current_run_env.value;
        let excludeValues = [];

        for (let i = 0; i < document.forms.length; i++) {
          let form = document.forms[i];
          if (form.current_run_env && form.current_run_env.value !== currentValue) {
            excludeValues.push(window.parseInt(form.current_run_env.value));
          }
        }

        let values = [];

        for (let i = 0; i < data.length; i++) {
          let envValue = data[i];
          if (excludeValues.indexOf(envValue.pk) < 0) {
            values.push([envValue.pk, envValue.fields.value]);
          }
        }

        setUpChoices(selectValueElem, values, false);
      },
    });
  });

  jQ('.js-remove-property').on('click', function () {
    let self = this;
    confirmDialog({
      message: 'Are you sure to remove this property?',
      title: 'Manage Test Run\'s Environment',
      yesFunc: function () {
        let parent = jQ(self).closest('form');
        let emptySelf = jQ(self).closest('li');
        let envValueId = jQ('input[type=hidden][name=current_run_env]', parent).get(0).value;

        postRequest({
          url: self.dataset.actionUrl,  // '/runs/env_value/delete/',
          data: {env_value: envValueId, runs: self.dataset.runId},
          errorMessage: 'Deleting value failed',
          success: function () { emptySelf.remove(); },
        });
      }
    });
  });

  jQ('.js-env-submit').on('click', function () {
    let dataset = this.dataset
      , selectField = jQ(this).prev()[0];

    let newValue = selectField.options[selectField.selectedIndex].innerHTML;
    let oldValue = jQ(selectField).prev().prev().val();

    let dupValues = [];
    jQ('input[type=hidden][name=current_run_env]').each(function (index, element) {
      if (element.value !== oldValue) {
        dupValues.push(element.value);
      }
      return true;
    });
    if (jQ.inArray(selectField.value, dupValues) >= 0) {
      showModal('The value is exist for this run');
      return false;
    }

    postRequest({
      url: dataset.actionUrl,
      data: {
        old_env_value: oldValue,
        new_env_value: selectField.value,
        runs: dataset.runId
      },
      success: function () {
        jQ('#' + dataset.envValueElemId).html(newValue).show();
        jQ(selectField).hide();
        jQ('#' + dataset.submitValueElemId).hide();
        jQ(selectField).prev().prev().val(selectField.value);
      },
    });
  });
}

function bindRemoveCCHandler() {
  jQ('.js-remove-cc').on('click', function () {
    let self = this;
    confirmDialog({
      message: 'Are you sure to delete this user from CC?',
      yesFunc: function () {
        constructRunCC(self.dataset.actionUrl, jQ('.js-cc-ul')[0], self.dataset.runId, {
          'do': 'remove',
          'user': self.dataset.userName
        });
      }
    });
  });
}

/**
 * Get the function to send a request to change case runs order.
 *
 * @param {number[]} caseRunIds - an array of case run ids.
 * @returns {(function(*=): void)|*} - the function to be called.
 */
Nitrate.TestRuns.getCaseRunsOrderChangeFunc = function (caseRunIds) {
  /**
   * Function to send a request to change case runs order.
   *
   * @param {number} newSortKey - the new sort key, e.g. 10.
   */
  return function (newSortKey) {
    patchRequest({
      url: '/ajax/case-runs/',
      data: {
        case_run: caseRunIds,
        target_field: 'sortkey',
        new_value: newSortKey
      }
    });
  };
};

Nitrate.TestRuns.Details.on_load = function () {
  // The run id is not necessary for binding the event handlers.
  let tagsView = new RunTagsView();
  tagsView.bindEventHandlers();

  jQ('.js-add-property').on('click', function () {
    new AddEnvPropertyDialog(this.dataset.runId, this.dataset.envGroupId).open();
  });

  // Observe the interface buttons
  if (jQ('#id_sort').length) {
    jQ('#id_sort').on('click', taggleSortCaseRun);
  }

  if (jQ('#id_check_box_highlight').prop('checked')) {
    jQ('.mine').addClass('highlight');
  }

  jQ('#id_check_box_highlight').on('click', function (e) {
    e = jQ('.mine');
    if (this.checked) {
      e.addClass('highlight');
    } else {
      e.removeClass('highlight');
    }
  });

  jQ('#id_blind_all_link').on('click', function () {
    if (!jQ('td[id^="id_loading_"]').length) {
      jQ(this).removeClass('locked');
    }
    if (jQ(this).is('.locked')) {
      //To disable the 'expand all' until all case runs are expanded.
      return false;
    } else {
      jQ(this).addClass('locked');
      let element = jQ(this).children();
      if (element.is('.collapse-all')) {
        this.title = 'Collapse all cases';
        blinddownAllCases(element[0]);
      } else {
        this.title = 'Expand all cases';
        blindupAllCases(element[0]);
      }
    }
  });

  // Observe the case run toggle and the comment form
  jQ('.expandable').on('click', function () {
    new CaseRunDetailExpansion(this, false).toggle();
  });

  jQ('#id_table_cases tbody .selector_cell').shiftcheckbox({
    checkboxSelector: ':checkbox',
    selectAll: '#id_table_cases .js-select-all'
  });

  // Auto show the case run contents.
  if (window.location.hash !== '') {
    jQ('a[href="' + window.location.hash + '"]').trigger('click');
  }

  // Filter Case-Run
  if (jQ('#filter_case_run').length) {
    jQ('#filter_case_run').on('click', function (){
      if (jQ('#id_filter').is(':hidden')){
        jQ('#id_filter').show();
        jQ(this).html(defaultMessages.link.hide_filter);
      } else {
        jQ('#id_filter').hide();
        jQ(this).html(defaultMessages.link.show_filter);
      }
    });
  }

  jQ('#btn_edit, #btnDeleteRun, .js-set-run-status').on('click', function () {
    window.location.assign(this.dataset.actionUrl);
  });

  jQ('#btn_clone, .js-update-case').on('click', function () {
    let caseRunIds = getSelectedCaseRunIDs();
    if (caseRunIds.length === 0) {
      return;
    }
    postToURL(this.dataset.actionUrl, {case_run: caseRunIds});
  });

  jQ('#btn_export_csv, #btn_export_xml').on('click', function () {
    let url = this.dataset.actionUrl + '&' + jQ('input[name=case_run]').serialize();
    window.location.assign(url);
  });

  jQ('.js-del-case').on('click', function () {
    delCaseRun();
  });
  jQ('.js-change-assignee').on('click', function () {
    changeCaseRunAssignee();
  });
  jQ('.js-add-issues').on('click', addIssueToBatchCaseRunsHandler);
  jQ('.js-remove-issues').on('click', removeIssueFromBatchCaseRunsHandler);
  jQ('.js-show-commentdialog').on('click', function () {
    showCommentForm();
  });

  jQ('.js-add-cc').on('click', function () {
    let user = window.prompt('Please type new email or username for CC.').trim();
    if (user) {
      constructRunCC(this.dataset.actionUrl, jQ('.js-cc-ul')[0], this.dataset.runId, {'do': 'add', 'user': user});
    }
  });
  bindRemoveCCHandler();

  bindEnvPropertyHandlers();

  jQ('.js-caserun-total, .js-status-subtotal').on('click', function () {
    let form = document.forms['filterCaseRunsForm'];
    form.case_run_status__name.value = this.dataset.statusName;
    form.submit();
  });

  jQ('.js-change-order').on('click', function (e) {
    const existingSortKey = parseInt(this.dataset.sortKey);
    Nitrate.Utils.changeOrderSortKey(
      Nitrate.TestRuns.getCaseRunsOrderChangeFunc([this.dataset.caseRunId]),
      isNaN(existingSortKey) ? undefined : existingSortKey
    );
    return false;
  });
};

Nitrate.TestRuns.New.on_load = function () {
  registerProductAssociatedObjectUpdaters(
    document.getElementById('id_product'),
    false,
    [
      {
        func: getBuildsByProductId,
        targetElement: document.getElementById('id_build'),
        addBlankOption: false,
      },
      {
        func: getVersionsByProductId,
        targetElement: document.getElementById('id_product_version'),
        addBlankOption: false,
      }
    ]
  );

  jQ('#add_id_product_version, #add_id_build').on('click', function () {
    return popupAddAnotherWindow(this, 'product');
  });
  jQ('.js-cancel-button').on('click', function () {
    window.history.go(-1);
  });
  jQ('img.blind_icon').on('click', caseDetailExpansionHandler);
  jQ('.js-remove-case').on('click', function () {
    removeItem(this.dataset.itemId, window.parseInt(this.dataset.estimatedTime));
  });
};

Nitrate.TestRuns.Edit.on_load = function () {
  registerProductAssociatedObjectUpdaters(
    document.getElementById('id_product'),
    false,
    [
      {
        func: getBuildsByProductId,
        targetElement: document.getElementById('id_build'),
        addBlankOption: false,
      },
      {
        func: getVersionsByProductId,
        targetElement: document.getElementById('id_product_version'),
        addBlankOption: false,
      }
    ]
  );

  if (jQ('#id_auto_update_run_status').prop('checked')) {
    jQ('#id_finished').prop({'checked': false, 'disabled': true});
  }
  jQ('#id_auto_update_run_status').on('click', function (){
    if (jQ('#id_auto_update_run_status').prop('checked')) {
      jQ('#id_finished').prop({'checked': false, 'disabled': true});
    } else {
      if (jQ('#id_finished').prop('disabled')) {
        jQ('#id_finished').prop('disabled', false);
      }
    }
  });
  jQ('#add_id_product_version, #add_id_build').on('click', function () {
    return popupAddAnotherWindow(this, 'product');
  });
};

Nitrate.TestRuns.Clone.on_load = function () {
  registerProductAssociatedObjectUpdaters(
    document.getElementById('id_product'),
    false,
    [
      {
        func: getBuildsByProductId,
        targetElement: document.getElementById('id_build'),
        addBlankOption: false,
      },
      {
        func: getVersionsByProductId,
        targetElement: document.getElementById('id_product_version'),
        addBlankOption: false,
      }
    ]
  );

  jQ('input[type=checkbox][name^=select_property_id_]').each(function () {
    jQ(this).on('click', function (){
      let parent = jQ(this).parent();
      jQ('select', parent).prop('disabled', !this.checked);
      jQ('input[type=hidden]', parent).prop('disabled', !this.checked);
    });
  });

  jQ('#add_id_product_version, #add_id_build').on('click', function () {
    return popupAddAnotherWindow(this, 'product');
  });
  jQ('.js-cancel-button').on('click', function () {
    window.history.go(-1);
  });
  jQ('.js-remove-button').on('click', function () {
    jQ(this).parents('.js-one-case').remove();
  });

  jQ('img.blind_icon').on('click', caseDetailExpansionHandler);
};

Nitrate.TestRuns.ChooseRuns.on_load = function () {
  jQ('#id_table_runs tbody tr td:nth-child(1)').shiftcheckbox({
    checkboxSelector: ':checkbox',
    selectAll: '#id_check_all_button'
  });

  jQ('.js-help-info').on('click', function () {
    jQ('#help_assign').show();
  });
  jQ('.js-close-help').on('click', function () {
    jQ('#help_assign').hide();
  });
  jQ('.js-toggle-button').on('click', caseDetailExpansionHandler);
};

Nitrate.TestRuns.AssignCase.on_load = function () {
  jQ('#id_table_cases tbody tr td:nth-child(1)').shiftcheckbox({
    checkboxSelector: ':checkbox:enabled',
    selectAll: '#id_check_all_button'
  });

  jQ('#id_check_all_button').prop(
    'disabled', jQ('id_table_cases tbody :checkbox:enabled').length === 0
  );

  jQ('.js-how-assign-case').on('click', function () {
    jQ('#help_assign').show();
  });
  jQ('.js-close-how-assign').on('click', function () {
    jQ('#help_assign').hide();
  });
  jQ('.js-toggle-button, .js-case-summary').on('click', caseDetailExpansionHandler);
};

/**
 * A function registered to the form submit event, from where to add comment to or change status for
 * a case run.
 *
 * @param {CaseRunDetailExpansion} expansion - the case run detail expansion object.
 * @param {HTMLElement} form - the form which triggered the event to update case run status.
 */
function updateCaseRunStatus(expansion, form) {
  let formData = Nitrate.Utils.formSerialize(form);
  let caseRunStatusId = formData.value;

  if (formData.comment !== '') {
    postRequest({
      url: '/comments/post/',
      data: formData,
      success: function () {
        updateCommentsCount(expansion.caseRunRow.find(':hidden[name=case]').val(), true);
      }
    });
  }

  // Update the object when changing the status
  if (caseRunStatusId !== '') {
    patchRequest({
      url: '/ajax/case-runs/',
      data: {
        case_run: [formData.object_pk],
        target_field: 'case_run_status',
        new_value: parseInt(caseRunStatusId),
      },
      success: function () {
        // Refresh the statistics section
        sendHTMLRequest({
          url: '/run/' + document.getElementById('value_run_id').value + '/statistics/',
          container: document.getElementById('run-statistics')
        })

        // Update the case run status icon
        let crs = Nitrate.TestRuns.CaseRunStatus;
        expansion.caseRunRow.find('.icon_status').each(function () {
          for (let i in crs) {
            if (typeof crs[i] === 'string' && jQ(this).is('.btn_' + crs[i])) {
              jQ(this).removeClass('btn_' + crs[i]);
            }
          }
          jQ(this).addClass('btn_' + Nitrate.TestRuns.CaseRunStatus[parseInt(caseRunStatusId) - 1]);
        });

        // Update related people
        expansion.caseRunRow.find('.link_tested_by').each(function () {
          this.href = 'mailto:' + Nitrate.User.email;
          jQ(this).html(Nitrate.User.username);
        });

        // Mark the case run to mine
        if (! expansion.caseRunRow.is('.mine')) {
          expansion.caseRunRow.addClass('mine');
        }
      }
    });
  }

  let expandNext =
      jQ('#id_check_box_auto_blinddown').prop('checked') &&
      caseRunStatusId !== '' &&
      !expansion.atLastRow;

  // TODO: the statistics has to be updated as well without reloading whole page.

  if (expandNext) {
    expansion.collapseCaseRunDetail();
    window.setTimeout(function () {
      expansion.expand();
      expansion.expandNextCaseRunDetail();
    }, 700);
  } else {
    expansion.showCaseRunDetailAjaxLoading();
    window.setTimeout(function () {
      expansion.expand();
    }, 700);
  }
}

function taggleSortCaseRun(event) {
  if (event.target.innerHTML !== 'Done Sorting') {
    jQ('#id_blind_all_link').remove(); // Remove blind all link

    // Remove case text
    jQ('#id_table_cases .hide').remove();

    // Remove blind down arrow link
    jQ('#id_table_cases .blind_icon').remove();

    // Use the title to replace the blind down title link
    jQ('#id_table_cases .blind_title_link').each(function () {
      const replaceWith = document.createElement('span');
      replaceWith.insertAdjacentHTML('afterbegin', this.innerHTML );
      jQ(this).replaceWith(replaceWith);
    });

    // Use the sortkey content to replace change sort key link
    jQ('#id_table_cases .mark').each(function () {
      jQ(this).parent().html(this.innerHTML);
    });

    jQ('#id_table_cases .case_content').remove();
    jQ('#id_table_cases .expandable').unbind();

    jQ('#id_sort').html('Done Sorting');

    jQ('#id_table_cases').tableDnD();
  } else {
    jQ('#id_table_cases input[type=checkbox]').prop({'checked': true, 'disabled': false});
    postToURL('ordercaserun/', {
      case_run: getSelectedCaseRunIDs()
    });
  }
}


/**
 * Remove issue from selected case runs
 *
 * @param {object} removeIssueInfo - object containing data for removing an issue from case run(s).
 * @param {number[]} removeIssueInfo.caseRunIds - an array of case runs from which to remove the issue.
 * @param {string} removeIssueInfo.issueKey - the issue to remove.
 * @param {number} removeIssueInfo.runId - the run id.
 * @param {Function} successCallback - the callback registered to success.
 */
function removeIssueFromCaseRuns(removeIssueInfo, successCallback) {
  if (removeIssueInfo.issueKey === undefined || removeIssueInfo.issueKey === '') {
    throw new Error('Missing issue key to remove.');
  }

  getRequest({
    url: '/run/' + removeIssueInfo.runId.toString() + '/issues/',
    data: {
      a: 'remove',
      case_run: removeIssueInfo.caseRunIds,
      issue_key: removeIssueInfo.issueKey
    },
    traditional: true,
    success: successCallback,
  });
}

function delCaseRun() {
  let caseRunIDs = getSelectedCaseRunIDs();

  if (caseRunIDs.length === 0) {
    return;
  }

  confirmDialog({
    message: 'You are about to delete ' + caseRunIDs.length + ' case run(s). Are you sure?',
    yesFunc: function () {
      postToURL('removecaserun/', {'case_run': caseRunIDs});
    }
  });
}

function addPropertyToEnv(runId, envValueId) {
  postRequest({
    url: '/runs/env_value/add/',
    data: {env_value: envValueId, runs: runId},
    success: function (data) {
      jQ('#dialog').hide();
      jQ('#env_area').html(data.fragment);
      bindEnvPropertyHandlers();
    },
  });
}

function constructRunCC(url, container, runId, parameters) {
  sendHTMLRequest({
    url: url,
    data: parameters,
    container: container,
    callbackAfterFillIn: function () {
      bindRemoveCCHandler();
      if (jQ('#message').length) {
        showModal(jQ('#message').html());
        return false;
      }
    }
  });
}

function changeCaseRunAssignee() {
  let selectedCaseRunIDs = getSelectedCaseRunIDs();
  if (!selectedCaseRunIDs.length) {
    showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
    return false;
  }

  let emailOrUsername = window.prompt('Please type new email or username for assignee');
  if (!emailOrUsername) {
    return false;
  }

  // First to get the user with input, if there is, then update selected case
  // runs' assignee to that user.
  getRequest({
    url: '/management/getinfo/',
    data: {info_type: 'users', username: emailOrUsername},
    errorMessage: 'Fail to get user ' + emailOrUsername,
    success: function (data) {
      // FIXME: Display multiple items and let user to select one
      if (data.length === 0) {
        showModal('Nothing found in database');
        return false;
      }

      if (data.length > 1) {
        showModal('Multiple instances reached, please define the condition more clear.');
        return false;
      }

      patchRequest({
        url: '/ajax/case-runs/',
        data: {
          case_run: selectedCaseRunIDs,
          target_field: 'assignee',
          new_value: parseInt(data[0].pk)
        },
      });
    },
  });
}

/**
 * Retrieve and return selected case run IDs from the container table whose id is id_table_cases.
 *
 * @returns {string[]} the selected test case IDs.
 */
function getSelectedCaseRunIDs() {
  let result = []
    , checkedCaseRuns = jQ('#id_table_cases input[name="case_run"]:checked');
  for (let i = 0; i < checkedCaseRuns.length; i++) {
    result.push(checkedCaseRuns[i].value);
  }
  return result;
}

//Added for choose runs and add cases to those runs
function serializeRunsFromInputList(table) {
  let elements = jQ('#' + table).parent().find('input[name="run"]:checked');
  let caseIds = [];
  elements.each(function () {
    if (typeof this.value === 'string') {
      caseIds.push(this.value);
    }
  });
  return caseIds;
}

/*
 * Click event handler for A .js-add-issues
 */
function addIssueToBatchCaseRunsHandler() {
  let caseRunIds = getSelectedCaseRunIDs().map(function (item) {
    return parseInt(item);
  });
  if (caseRunIds.length === 0) {
    showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
  } else {
    let addIssueInfo = jQ(this).data('addIssueInfo');
    addIssueInfo.caseRunIds = caseRunIds;
    let dialog = new AddIssueDialog();
    dialog.dialog.dialog('option', 'reloadPage', true);
    dialog.open(addIssueInfo);
  }
}


/*
 * Click event handler for A .js-remove-issues
 */
function removeIssueFromBatchCaseRunsHandler() {
  let caseRunIds = getSelectedCaseRunIDs().map(function (item) {
    return parseInt(item);
  });

  if (caseRunIds.length === 0) {
    showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
  } else {
    let removeIssueInfo = jQ(this).data('removeIssueInfo');
    removeIssueInfo.caseRunIds = caseRunIds;

    let removeIssueDialog = jQ('div[id=showDialog]').dialog({
      title: 'Remove issue key',
      modal: true,
      resizable: false,
      buttons: {
        Ok: function () {
          // Don't care about closing or destroying current dialog.
          // Whole page will be reloaded.
          removeIssueInfo.issueKey = jQ(this).find('input[id=issueKeyToRemove]').val();
          removeIssueFromCaseRuns(removeIssueInfo);
        },
        Cancel: function () {
          jQ(this).dialog('close');
        }
      }
    });

    removeIssueDialog.html(
      '<label for="issueKeyToRemove">Issue key</label><br>' +
      '<input type="text" id="issueKeyToRemove">');
    removeIssueDialog.dialog('open');
  }
}

function showCommentForm() {
  let caseRunIds = getSelectedCaseRunIDs();

  if (caseRunIds.length === 0) {
    showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
    return;
  }

  let commentTextbox = document.getElementById('newCommentText');

  let dialog = jQ('#addCommentDialog').dialog({
    autoOpen: false,
    height: 260,
    width: 380,
    modal: true,
    buttons: {
      OK: function () {
        let comment = commentTextbox.value.trim().slice(0, -1);
        if (comment.length === 0) {
          return;
        }

        // Clear the text for the input next time.
        commentTextbox.value = '';

        postRequest({
          url: '/runs/case-runs/comment-many/',
          data: {comment: comment, run: caseRunIds},
          traditional: true,
        });

        dialog.dialog('close');
        dialog.dialog('destroy');
      },
      Cancel: function () {
        dialog.dialog('close');
      }
    }
  });

  dialog.dialog('open');
}

jQ(document).ready(function (){
  jQ('.btnBlueCaserun').mouseover(function () {
    jQ(this).find('ul').show();
  }).mouseout(function () {
    jQ(this).find('ul').hide();
  });
  jQ('ul.statusOptions a').click(function () {
    let option = jQ(this).data('statusid');
    if (option === '') {
      return false;
    }
    let objectPks = getSelectedCaseRunIDs();
    if (!objectPks.length) {
      showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
      return false;
    }

    confirmDialog({
      message: defaultMessages.confirm.change_case_status,
      yesFunc: function () {
        patchRequest({
          url: '/ajax/case-runs/',
          data: {
            case_run: objectPks,
            target_field: 'case_run_status',
            new_value: option
          },
        });
      }
    });
  });
});

function getAddLinkDialog() {
  return jQ('#addlink_dialog');
}

/**
 * Initialize dialog for getting information about new link, which is attached
 * to an arbitrary instance of TestCaseRun
 *
 * @param {string} linkTarget - the name of Model to whose instance new link will be linked.
 */
function initializeAddLinkDialog(linkTarget) {
  let dialog = getAddLinkDialog();

  dialog.dialog({
    autoOpen: false,
    modal: true,
    resizable: false,
    height: 300,
    width: 400,
    open: function () {
      jQ(this).off('submit').on('submit', function (e) {
        e.stopPropagation();
        e.preventDefault();
        jQ(this).dialog('widget').find('span:contains("OK")').click();
      });
    },
    buttons: {
      'OK': function () {
        // TODO: validate name and url
        postRequest({
          url: '/linkref/add/',
          data: {
            name: jQ('#testlog_name').prop('value'),
            url: jQ('#testlog_url').prop('value'),
            target: jQ(this).dialog('option', 'target'),
            target_id: jQ(this).dialog('option', 'target_id')
          },
          success: function () {
            dialog.dialog('close');
            let expansion = dialog.dialog('option', 'caseRunDetailExpansion');
            expansion.showLoadingAnimation = true;
            expansion.expand();
          },
        });
      },
      'Cancel': function () {
        jQ(this).dialog('close');
      }
    },
    beforeClose: function () {
      // clean name and url for next input
      jQ('#testlog_name').val('');
      jQ('#testlog_url').val('');

      return true;
    },
    // Customize variables
    // Used for adding links to an instance of TestCaseRun
    target: linkTarget,
    /* ATTENTION: target_id can be determined when open this dialog, and
     * this must be set
     */
    target_id: null
  });
}
