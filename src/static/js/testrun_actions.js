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

function toggleTestCaseContents(
  templateType, container, contentContainer, objectPk, caseTextVersion, caseRunId, callback) {
  // TODO: should container and contentContainer be in string type?

  container =
    typeof container === 'string' ? jQ('#' + container)[0] : container;

  contentContainer =
    typeof contentContainer === 'string' ?
      jQ('#' + contentContainer)[0] : contentContainer;

  jQ(contentContainer).toggle();

  if (jQ('#id_loading_' + objectPk).length) {
    sendHTMLRequest({
      url: Nitrate.http.URLConf.reverse({
        name: 'case_details',
        arguments: {id: objectPk}
      }),
      data: {
        template_type: templateType,
        case_text_version: caseTextVersion,
        case_run_id: caseRunId
      },
      container: contentContainer,
      callbackAfterFillIn: callback
    });
  }

  toggleExpandArrow({
    caseRowContainer: jQ(container),
    expandPaneContainer: jQ(contentContainer)
  });
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

function cloneRunsClickHandler() {
  postToURL(jQ(this).data('param'), Nitrate.Utils.formSerialize(this.form), 'get');
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

    iDeferLoading: Nitrate.TestRuns.Search.numberOfRuns,

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
      jQ('.js-clone-testruns').on('click', cloneRunsClickHandler);
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


function updateIssuesCountInCaseRunRow(caseRunRow, caseRunIssuesCount) {
  let caseRunIssuesCountSpan = jQ(caseRunRow).find('span[id$="_case_issues_count"]');
  caseRunIssuesCountSpan.text(caseRunIssuesCount);
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

          // After adding an issue successfully, number of issues inside the run
          // page has to be updated and reload case run detail content eventually.
          success: function (data) {
            // After succeeding to add issue, we close the add dialog.
            dialog.dialog('close');

            let reloadInfo = dialog.dialog('option', 'reloadInfo');

            // TODO: consider now to reload whole page.
            //       consider with the else section to update partial page
            //       content and reload expanded case run details.

            if (reloadInfo.reloadPage) {
              window.location.reload();
            } else {
              // When add issue to a case run, only need to reload the updated case run.
              // Update issues count associated with just updated case run
              for (let caseRunId in addIssueInfo.caseRunIds) {
                let caseRunIssuesCount = data.caserun_issues_count[caseRunId];
                updateIssuesCountInCaseRunRow(reloadInfo.caseRunRow, caseRunIssuesCount);
              }
              showTheNumberOfCaseRunIssues(data.run_issues_count, addIssueInfo.runId);
              constructCaseRunZone(
                reloadInfo.caseRunDetailRow, reloadInfo.caseRunRow, addIssueInfo.caseId);
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

AddIssueDialog.prototype.open = function (addIssueInfo, reloadInfo) {
  if (addIssueInfo.caseRunIds === undefined || !Array.isArray(addIssueInfo.caseRunIds)) {
    throw new Error('addIssueInfo.caseRunIDs must be an array including case run IDs.');
  }

  let dialog = this.dialog;

  dialog.dialog('option', 'title', 'Add issue to case run');
  dialog.dialog('option', 'reloadInfo', reloadInfo);
  dialog.dialog('option', 'addIssueInfo', addIssueInfo);

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

Nitrate.TestRuns.Details.on_load = function () {
  let addIssueDialog = new AddIssueDialog();

  jQ('.js-add-property').on('click', function () {
    let params = jQ(this).data('params');
    new AddEnvPropertyDialog(params[0], params[1]).open();
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
    let c = jQ(this).parent(); // Case run row
    let cContainer = c.next(); // Next row to show case run details
    let caseId = c.find('input[name="case"]')[0].value;

    /* eslint func-style:off */
    // FIXME: move this function outside of this callback
    let callback = function () {
      // Observe the update case run status/comment form
      cContainer.parent().find('.update_form').off('submit').on('submit', updateCaseRunStatus);

      cContainer.parent().find('.form_comment').off('submit').on('submit', function (e) {
        e.stopPropagation();
        e.preventDefault();
        if (!window.confirm(defaultMessages.confirm.remove_comment)) {
          return false;
        }
        removeComment(this, function () {
          updateCommentsCount(c.find(':hidden[name=case]').val(), false);
          constructCaseRunZone(cContainer[0], c[0], caseId);
        });
      });

      cContainer.find('.js-status-button').on('click', function () {
        this.form.value.value = jQ(this).data('formvalue');
      });
      cContainer.find('.js-show-comments').on('click', function () {
        toggleDiv(this, jQ(this).data('param'));
      });
      cContainer.find('.js-show-changelog').on('click', function () {
        toggleDiv(this, jQ(this).data('param'));
      });
      cContainer.find('.js-add-caserun-issue').on('click', function () {
        addIssueDialog.open(jQ(this).data('params'), {
          caseRunRow: c[0],
          caseRunDetailRow: cContainer[0]
        });
      });
      cContainer.find('.js-remove-caserun-issue').on('click', function (){
        removeIssueFromCaseRuns(jQ(this).data('params'), {
          caseRunRow: c[0],
          caseRunDetailRow: cContainer[0]
        });
      });
      cContainer.find('.js-add-testlog').on('click', function (){
        let params = jQ(this).data('params');
        addLinkToCaseRun(this, params[0], params[1]);
      });
      cContainer.find('.js-remove-testlog').on('click', function (){
        removeLink(this, window.parseInt(jQ(this).data('param')));
      });
    };

    let caseRunId = c.find('input[name="case_run"]')[0].value;
    let caseTextVersion = c.find('input[name="case_text_version"]')[0].value;

    toggleTestCaseRunPane({
      'callback': callback,
      'caseId': caseId,
      'caserunId': caseRunId,
      'caseTextVersion': caseTextVersion,
      'caserunRowContainer': c,
      'expandPaneContainer': cContainer
    });
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

  //bind click to status btn
  jQ('.btn_status').on('click', function () {
    let from = jQ(this).siblings('.btn_status:disabled')[0].title;
    let to = this.title;
    if (jQ('span#' + to + ' a').text() === '0') {
      let htmlstr =
        '[<a href="javascript:void(0)" ' +
        'onclick="showCaseRunsWithSelectedStatus(jQ(\'#id_filter\')[0], ' + jQ(this).prop('crs_id') + ')">0</a>]';
      jQ('span#' + to).html(htmlstr);
    }
    if (jQ('span#' + from + ' a').text() === '1') {
      jQ('span#' + from).html('[<a>1</a>]');
    }
    jQ('span#' + to + ' a').text(window.parseInt(jQ('span#' + to + ' a').text()) + 1);
    jQ('span#' + from + ' a').text(window.parseInt(jQ('span#' + from + ' a').text()) - 1);

    let caseRunCount = window.parseInt(jQ('span#TOTAL').next().text()) || 0;
    let passedCaseRunCount = window.parseInt(jQ('span#PASSED a').text()) || 0;
    let errorCaseRunCount = window.parseInt(jQ('span#ERROR a').text()) || 0;
    let failedCaseRunCount = window.parseInt(jQ('span#FAILED a').text()) || 0;
    let waivedCaseRunCount = window.parseInt(jQ('span#WAIVED a').text()) || 0;

    let completedCasesCount = passedCaseRunCount + errorCaseRunCount + failedCaseRunCount + waivedCaseRunCount;
    let completePercent = 100 * (completedCasesCount / caseRunCount).toFixed(2);
    let unsuccessfulCasesCount = errorCaseRunCount + failedCaseRunCount;
    let failedPercent = 100 * (unsuccessfulCasesCount / completedCasesCount).toFixed(2);

    jQ('span#complete_percent').text(completePercent);
    jQ('div.progress-inner').prop('style', 'width:' + completePercent + '%');
    jQ('div.progress-failed').prop('style', 'width:' + failedPercent + '%');
  });

  jQ('#btn_edit').on('click', function () {
    let params = jQ(this).data('params');
    window.location.href = params[0] + '?from_plan=' + params[1];
  });
  jQ('#btn_clone').on('click', function () {
    postToURL(jQ(this).data('param'), {
      case_run: getSelectedCaseRunIDs()
    });
  });
  jQ('#btn_delete').on('click', function () {
    window.location.href = jQ(this).data('param');
  });
  jQ('#btn_export_csv').on('click', function () {
    window.location.href = jQ(this).data('param') + '?format=csv&' + jQ('#id_form_case_runs').serialize();
  });
  jQ('#btn_export_xml').on('click', function () {
    window.location.href = jQ(this).data('param') + '?format=xml&' + jQ('#id_form_case_runs').serialize();
  });
  jQ('.js-remove-tag').on('click', function () {
    let params = jQ(this).data('params');
    removeRuntag(jQ('.js-tag-ul')[0], params[0], params[1]);
  });
  jQ('.js-add-tag').on('click', function () {
    addRunTag(jQ('.js-tag-ul')[0], jQ(this).data('param'));
  });
  jQ('.js-set-running').on('click', function () {
    window.location.href = jQ(this).data('param') + '?finished=0';
  });
  jQ('.js-set-finished').on('click', function () {
    window.location.href = jQ(this).data('param') + '?finished=1';
  });
  jQ('.js-del-case').on('click', function () {
    delCaseRun();
  });
  jQ('.js-update-case').on('click', function () {
    postToURL(jQ(this).data('param'), {
      case_run: getSelectedCaseRunIDs()
    });
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
    addRunCC(jQ(this).data('param'), jQ('.js-cc-ul')[0]);
  });
  jQ('.js-remove-cc').on('click', function () {
    let params = jQ(this).data('params');
    removeRunCC(params[0], params[1], jQ('.js-cc-ul')[0]);
  });
  jQ('.js-edit-property').on('click', function () {
    let params = jQ(this).data('params');
    editValue(jQ(this).parents('form.js-run-env')[0], params[0], params[1], params[2]);
  });
  jQ('.js-remove-property').on('click', function () {
    removeProperty(jQ(this).data('param'), this);
  });
  jQ('.js-env-submit').on('click', function () {
    let params = jQ(this).data('params');
    submitValue(params[0], params[1], params[2], jQ(this).prev()[0], params[3]);
  });
  jQ('.js-caserun-total').on('click', function () {
    showCaseRunsWithSelectedStatus(jQ('#id_filter')[0], '');
  });
  jQ('.js-status-subtotal').on('click', function () {
    showCaseRunsWithSelectedStatus(jQ('#id_filter')[0], jQ(this).data('param'));
  });
  jQ('.js-change-order').on('click', function () {
    let params = jQ(this).data('params');
    changeCaseRunOrder(params[0], params[1], params[2]);
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

  if (jQ('#testcases').length) {
    jQ('#testcases').dataTable({'bPaginate': false, 'bFilter': false, 'bProcessing': true});
  }

  jQ('#add_id_product_version, #add_id_build').on('click', function () {
    return popupAddAnotherWindow(this, 'product');
  });
  jQ('.js-cancel-button').on('click', function () {
    window.history.go(-1);
  });
  jQ('.js-case-summary').on('click', function () {
    toggleTestCaseContents(jQ(this).data('param'));
  });
  jQ('.js-remove-case').on('click', function () {
    let params = jQ(this).data('params');
    removeItem(params[0], params[1]);
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
};

Nitrate.TestRuns.ChooseRuns.on_load = function () {
  jQ('#id_table_runs tbody tr td:nth-child(1)').shiftcheckbox({
    checkboxSelector: ':checkbox',
    selectAll: '#id_check_all_button'
  });

  jQ('.js-update-button').on('click', function () {
    insertCasesIntoTestRun();
  });
  jQ('.js-help-info').on('click', function () {
    jQ('#help_assign').show();
  });
  jQ('.js-close-help').on('click', function () {
    jQ('#help_assign').hide();
  });
  jQ('.js-toggle-button').on('click', function () {
    let c = jQ(this).parents('.js-one-case');
    let cContainer = c.next();
    let caseId = c.find('input[name="case"]').val();
    toggleTestCasePane({'case_id': caseId, 'casePaneContainer': cContainer}, function () {
      cContainer.children().prop('colspan', 9);
    });
    toggleExpandArrow({
      'caseRowContainer': c,
      'expandPaneContainer': cContainer
    });
  });
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
  jQ('.js-toggle-button, .js-case-summary').on('click', function () {
    toggleTestCaseContents(jQ(this).data('param'));
  });
};

/**
 * A callback called after a comment is added to a case run or a case run status is updated with a
 * short comment.
 *
 * @param {jQuery} caseRunRow - the container representing the case run table row.
 * @param {jQuery} expandedCaseRunDetailRow - the container representing the expanded table row
 *                                            containing case run details.
 * @param {string} caseRunStatusId - case run status ID.
 */
function updateCaseRunDetailAfterCommentIsAdded(caseRunRow, expandedCaseRunDetailRow, caseRunStatusId) {
  // Update the contents
  if (caseRunStatusId !== '') {
    // Update the case run status icon
    let crs = Nitrate.TestRuns.CaseRunStatus;
    caseRunRow.find('.icon_status').each(function () {
      for (let i in crs) {
        if (typeof crs[i] === 'string' && jQ(this).is('.btn_' + crs[i])) {
          jQ(this).removeClass('btn_' + crs[i]);
        }
      }
      jQ(this).addClass('btn_' + Nitrate.TestRuns.CaseRunStatus[parseInt(caseRunStatusId) - 1]);
    });

    // Update related people
    caseRunRow.find('.link_tested_by').each(function () {
      this.href = 'mailto:' + Nitrate.User.email;
      jQ(this).html(Nitrate.User.username);
    });
  }

  // Mark the case run to mine
  if (!caseRunRow.is('.mine')) {
    caseRunRow.addClass('mine');
  }

  // Blind down next case
  let expandableElem = caseRunRow.find('.expandable');
  expandableElem.trigger('click');
  if (jQ('#id_check_box_auto_blinddown').prop('checked') && caseRunStatusId !== '') {
    let nextTitle = expandedCaseRunDetailRow.next();
    if (!nextTitle.length) {
      return;
    }
    if (nextTitle.next().is(':hidden')) {
      nextTitle.find('.expandable').trigger('click');
    }
  } else {
    expandableElem.trigger('click');
  }
}

/**
 * A function registered to the form submit event, from where to add comment to or change status for a case run.
 *
 * @param {Event} e - the DOM event.
 */
function updateCaseRunStatus(e) {
  e.stopPropagation();
  e.preventDefault();

  let caseRunDetailCell = jQ(this).parents().eq(3);
  let expandedCaseRunDetailRow = caseRunDetailCell.parent();
  let caseRunRow = expandedCaseRunDetailRow.prev();

  let formData = Nitrate.Utils.formSerialize(this);
  let caseRunStatusId = formData.value;

  // Add comment
  if (formData.comment !== '') {
    // Reset the content to loading
    caseRunDetailCell.html(constructAjaxLoading('id_loading_' + formData.case_id));

    submitComment(jQ('<div>')[0], formData, function () {
      updateCommentsCount(caseRunRow.find(':hidden[name=case]').val(), true);
      if (caseRunStatusId === '') {
        updateCaseRunDetailAfterCommentIsAdded(caseRunRow, expandedCaseRunDetailRow, caseRunStatusId);
      }
    });
  }

  // Update the object when changing the status
  if (caseRunStatusId !== '') {
    // Reset the content to loading
    caseRunDetailCell.html(constructAjaxLoading('id_loading_' + formData.case_id));

    updateObject({
      url: '/ajax/update/case-run-status',
      contentType: formData.content_type,
      objectPk: formData.object_pk,
      field: formData.field,
      value: caseRunStatusId,
      valueType: 'int',
      callback: function () {
        updateCaseRunDetailAfterCommentIsAdded(caseRunRow, expandedCaseRunDetailRow, caseRunStatusId);
      }
    });
  }
}

function changeCaseRunOrder(runId, caseRunId, sortKey) {
  let nsk = window.prompt('Enter your new order number', sortKey); // New sort key

  if (!nsk) {
    return false;
  }

  if (isNaN(nsk)) {
    showModal(
      'The value must be a integer number and limit between 0 to 32300.',
      'Input Error'
    );
    return false;
  }

  if (nsk > 32300 || nsk < 0) {
    showModal('The value must be a integer number and limit between 0 to 32300.');
    return false;
  }

  if (nsk === sortKey) {
    showModal('Nothing changed');
    return false;
  }

  updateObject({
    contentType: 'testruns.testcaserun',
    objectPk: caseRunId,
    field: 'sortkey',
    value: nsk,
    valueType: 'int'
  });
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
      jQ(this).replaceWith((jQ('<span>')).html(this.innerHTML));
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

function constructCaseRunZone(container, titleContainer, caseId) {
  if (container) {
    let td = jQ('<td>', {'id': 'id_loading_' + caseId, 'colspan': 12});
    td.html(constructAjaxLoading());
    jQ(container).html(td);
  }

  if (titleContainer) {
    let link = jQ(titleContainer).find('.expandable');
    link.trigger('click');
    link.trigger('click');
  }
}


function removeIssueFromCaseRuns(removeIssueInfo, reloadInfo) {
  if (removeIssueInfo.issueKey === undefined || removeIssueInfo.issueKey === '') {
    throw new Error('Missing issue key to remove.');
  }

  getRequest({
    url: '/run/' + removeIssueInfo.runId + '/issues/',
    data: {
      a: 'remove',
      case_run: removeIssueInfo.caseRunIds,
      issue_key: removeIssueInfo.issueKey
    },
    traditional: true,
    success: function (data) {
      if (reloadInfo.reloadPage) {
        window.location.reload();
      } else {
        let caseRunIssuesCount = data.caserun_issues_count[removeIssueInfo.caseRunId];
        updateIssuesCountInCaseRunRow(reloadInfo.caseRunRow, caseRunIssuesCount);
        showTheNumberOfCaseRunIssues(data.run_issues_count, removeIssueInfo.runId);
        constructCaseRunZone(
          reloadInfo.caseRunDetailRow, reloadInfo.caseRunRow, removeIssueInfo.caseId);
      }
    },
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

function editValue(form, hidebox, selectid, submitid) {
  jQ('#' + hidebox).hide();
  jQ('#' + selectid).show();
  jQ('#' + submitid).show();

  let data = Nitrate.Utils.formSerialize(form);
  let envPropertyId = data.env_property_id;

  getRequest({
    url: '/management/getinfo/',
    data: {info_type: 'env_values', env_property_id: envPropertyId},
    errorMessage: 'Update values failed',
    success: function (data) {
      let currentValue = jQ('input[type=hidden][name=current_run_env]:eq(0)', form);
      let excludeValues = [];

      jQ('input[type=hidden][name=current_run_env]').each(function (index, element) {
        if (element.value !== currentValue.val()) {
          excludeValues.push(window.parseInt(element.value));
        }
        return true;
      });

      let values = [];
      jQ.each(data, function (index, value) {
        if (jQ.inArray(value.pk, excludeValues) < 0) {
          values.push([value.pk, value.fields.value]);
        }
        return true;
      });

      setUpChoices(jQ('#' + selectid)[0], values, false);
    },
  });
}

function submitValue(runId, value, hidebox, selectField, submitid) {
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
    url: '/runs/env_value/change/',
    data: {
      old_env_value: oldValue,
      new_env_value: selectField.value,
      runs: runId
    },
    success: function () {
      jQ('#' + hidebox).html(newValue).show();
      jQ(selectField).hide();
      jQ('#' + submitid).hide();
      jQ(selectField).prev().prev().val(selectField.value);
    },
  });
}

function removeProperty(runId, element) {
  confirmDialog({
    message: 'Are you sure to remove this porperty?',
    title: 'Manage Test Run\'s Environment',
    yesFunc: function () {
      let parent = jQ(element).closest('form');
      let emptySelf = jQ(element).closest('li');
      let envValueId = jQ('input[type=hidden][name=current_run_env]', parent).get(0).value;

      postRequest({
        url: '/runs/env_value/delete/',
        data: {env_value: envValueId, runs: runId},
        errorMessage: 'Deleting value failed',
        success: function () { emptySelf.remove(); },
      });
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
      jQ('.js-edit-property').on('click', function () {
        let params = jQ(this).data('params');
        editValue(jQ(this).parents('form.js-run-env')[0], params[0], params[1], params[2]);
      });
      jQ('.js-remove-property').on('click', function () {
        removeProperty(jQ(this).data('param'), this);
      });
      jQ('.js-env-submit').on('click', function () {
        let params = jQ(this).data('params');
        submitValue(params[0], params[1], params[2], jQ(this).prev()[0], params[3]);
      });
    },
  });
}

function addRunTag(container, runId) {
  let tag = window.prompt('Please type new tag.');
  if (!tag) {
    return false;
  }

  // FIXME: should be a POST request
  sendHTMLRequest({
    url: '/management/tags/',
    data: {a: 'add', run: runId, tags: tag},
    container: container,
    callbackAfterFillIn: function () {
      jQ('.js-remove-tag').on('click', function () {
        let params = jQ(this).data('params');
        removeRuntag(jQ('.js-tag-ul')[0], params[0], params[1]);
      });
    }
  });
}

function removeRuntag(container, runId, tag) {
  // FIXME: should be a POST request
  sendHTMLRequest({
    url: '/management/tags/',
    data: {a: 'remove', run: runId, tags: tag},
    container: container,
    callbackAfterFillIn: function () {
      jQ('.js-remove-tag').on('click', function () {
        let params = jQ(this).data('params');
        removeRuntag(jQ('.js-tag-ul')[0], params[0], params[1]);
      });
    }
  });
}

function constructRunCC(container, runId, parameters) {
  sendHTMLRequest({
    url: '/run/' + runId + '/cc/',
    data: parameters,
    container: container,
    callbackAfterFillIn: function () {
      jQ('.js-remove-cc').on('click', function () {
        let params = jQ(this).data('params');
        removeRunCC(params[0], params[1], jQ('.js-cc-ul')[0]);
      });
      if (jQ('#message').length) {
        showModal(jQ('#message').html());
        return false;
      }
    }
  });
}

function addRunCC(runId, container) {
  let user = window.prompt('Please type new email or username for CC.');
  if (!user) {
    return false;
  }
  constructRunCC(container, runId, {'do': 'add', 'user': user});
}

function removeRunCC(runId, user, container) {
  confirmDialog({
    message: 'Are you sure to delete this user from CC?',
    yesFunc: function () {
      constructRunCC(container, runId, {'do': 'remove', 'user': user});
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

      updateObject({
        contentType: 'testruns.testcaserun',
        objectPk: selectedCaseRunIDs,
        field: 'assignee',
        value: data[0].pk,
        valueType: 'int'
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

function showCaseRunsWithSelectedStatus(form, statusId) {
  form.case_run_status__pk.value = statusId;
  jQ(form).find('input[type="submit"]').trigger('click');
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

function insertCasesIntoTestRun() {
  confirmDialog({
    message: 'Are you sure to add cases to the run?',
    yesFunc: function () {
      let caseIds = [];
      jQ('[name="case"]').each(function () {
        caseIds.push(this.value);
      });
      let params = {
        testrun_ids: serializeRunsFromInputList('id_table_runs'),
        case_ids: caseIds
      };
      postToURL('../chooseruns/', params, 'POST');
    }
  });
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
    let reloadInfo = jQ(this).data('reloadInfo');
    let dialog = new AddIssueDialog();
    dialog.open(addIssueInfo, reloadInfo);
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
    let reloadInfo = jQ(this).data('reloadInfo');
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
          removeIssueFromCaseRuns(removeIssueInfo, reloadInfo);
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
          url: '/caserun/comment-many/',
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
        updateObject({
          contentType: 'testruns.testcaserun',
          objectPk: objectPks,
          field: 'case_run_status',
          value: option,
          valueType: 'int'
        });
      }
    });
  });
});

function getAddLinkDialog() {
  return jQ('#addlink_dialog');
}

/**
 * Do AJAX request to backend to remove a link
 *
 * @param {HTMLElement} sender - the HTML element triggering the event to remove a link.
 * @param {number} linkId - the ID of an arbitrary link.
 */
function removeLink(sender, linkId) {
  let url = '/linkref/remove/' + linkId + '/';
  postRequest({url: url, success: function () {
    let liNode = sender.parentNode;
    liNode.parentNode.removeChild(liNode);
  }});
}

/**
 * Add link to case run
 *
 * @param {HTMLElement} sender - the Add link button, which is pressed to fire this event.
 * @param {number} caseId - the test case ID.
 * @param {number} caseRunId - the test case run ID.
 */
function addLinkToCaseRun(sender, caseId, caseRunId) {
  let dialog = getAddLinkDialog();

  dialog.dialog('option', 'target_id', caseRunId);
  // These two options are used for reloading TestCaseRun when successfully.
  let container = jQ(sender).parents('.case_content.hide')[0];
  dialog.dialog('option', 'container', container);
  let titleContainer = jQ(container).prev()[0];
  dialog.dialog('option', 'title_container', titleContainer);
  dialog.dialog('option', 'case_id', caseId);
  dialog.dialog('open');
}

/* eslint no-unused-vars: off */
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

            // Begin to construct case run area
            constructCaseRunZone(
              dialog.dialog('option', 'container'),
              dialog.dialog('option', 'title_container'),
              dialog.dialog('option', 'case_id')
            );
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


/**
 * Toggle TestCaseRun panel to edit a case run in run page.
 *
 * @param {object} options - options for toggling the test case run pane.
 * @param {HTMLElement} options.caserunRowContainer - the container element containing the test case run row.
 * @param {HTMLElement} options.expandPaneContainer - the container element to be expanded for the associated test case
 *                                                    run.
 * @param {number} options.caseId - the associated test case ID.
 * @param {number} options.caserunId - the test case run ID.
 * @param {number} options.caseTextVersion - the test case' text version.
 * @param {Function} options.callback - a function called after the content is filled in the expanded container.
 */
function toggleTestCaseRunPane(options) {
  let container = options.expandPaneContainer;
  container.toggle();

  if (container.find('.ajax_loading').length) {
    sendHTMLRequest({
      url: '/case/' + options.caseId + '/caserun-detail-pane/',
      container: container,
      callbackAfterFillIn: options.callback,
      data: {
        case_run_id: options.caserunId,
        case_text_version: options.caseTextVersion
      },
    });
  }

  toggleExpandArrow({
    caseRowContainer: options.caserunRowContainer,
    expandPaneContainer: container
  });
}
