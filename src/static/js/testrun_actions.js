Nitrate.TestRuns = {};
Nitrate.TestRuns.List = {};
Nitrate.TestRuns.Details = {};
Nitrate.TestRuns.New = {};
Nitrate.TestRuns.Edit = {};
Nitrate.TestRuns.Execute = {};
Nitrate.TestRuns.Clone = {};
Nitrate.TestRuns.ChooseRuns = {};
Nitrate.TestRuns.AssignCase = {};

Nitrate.TestRuns.List.on_load = function() {
  bind_version_selector_to_product(true, jQ('#id_product')[0]);
  bind_build_selector_to_product(true, jQ('#id_product')[0]);

  Nitrate.Utils.enableShiftSelectOnCheckbox('run_selector');

  if (jQ('#testruns_table').length) {
    jQ('#id_check_all_runs').on('click',function(e) {
      clickedSelectAll(this, jQ('#testruns_table')[0], 'run');
    });
  }
  if (jQ('#id_people_type').length) {
    jQ('#id_search_people').attr('name', jQ('#id_people_type').val());
    jQ('#id_people_type').on('change', function() {
      jQ('#id_search_people').attr('name', jQ('#id_people_type').val());
    });
  }

  if (jQ('#run_column_add').length) {
    jQ('#run_column_add').on('change', function(t) {
      switch(this.value) {
        case 'col_plan':
          jQ('#col_plan_head').show();
          jQ('.col_plan_content').show();
          jQ('#col_plan_option').hide();
          break;
      }
    });
  }

  if (!jQ('#testruns_table').hasClass('js-advance-search-runs')) {
    jQ('#testruns_table').dataTable({
      "iDisplayLength": 20,
      "sPaginationType": "full_numbers",
      "bFilter": false,
      "bLengthChange": false,
      "aaSorting": [[ 1, "desc" ]],
      "bProcessing": true,
      "bServerSide": true,
      "sAjaxSource": "/runs/ajax/" + this.window.location.search,
      "aoColumns": [
        {"bSortable": false },
        {"sType": "numeric"},
        {"sType": "html"},
        {"sType": "html"},
        {"sType": "html"},
        {"bVisible": false},
        null,
        null,
        null,
        {"sType": "numeric", "bSortable": false},
        null,
        {"bSortable": false }
      ],
      "oLanguage": { "sEmptyTable": "No run was found." }
    });
  }
  jQ('.js-clone-testruns').on('click', function() {
    postToURL(jQ(this).data('param'), Nitrate.Utils.formSerialize(this.form), 'get');
  });
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

    beforeClose: function(event, ui) {
      // Whenever dialog is closed, previous input issue key should be cleared
      // in order to not confuse user when use next time.
      jQ(this).find('input:text').val('');
    },

    buttons: {
      Add: function() {
        let dialog = jQ(this);
        let selectedIssueTracker = dialog
            .find('select[id="issue_tracker_id"] option:selected');
        let issueTrackerID = selectedIssueTracker.val();
        let validateRegex = selectedIssueTracker.data('validate-regex');
        let issueInputSection = dialog.find('div#' + selectedIssueTracker.data('tab'));

        let issueKey = issueInputSection.find('input[name="issue_key"]').val();
        let optLinkExternalTracker = issueInputSection.find('input[name="link_external_tracker"]');
        let addIssueInfo = dialog.dialog('option', 'addIssueInfo');

        if (! new RegExp(validateRegex).test(issueKey)) {
          window.alert('Issue key is malformated.');
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
          success: function(data) {
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

      Cancel: function() {
        jQ(this).dialog('close');
      }
    }
  });
}

AddIssueDialog.prototype.open = function(addIssueInfo, reloadInfo) {
  if (addIssueInfo.caseRunIds === undefined || !Array.isArray(addIssueInfo.caseRunIds))
    throw new Error('addIssueInfo.caseRunIDs must be an array including case run IDs.');

  let dialog = this.dialog;

  dialog.dialog('option', 'title', 'Add issue to case run');
  dialog.dialog('option', 'reloadInfo', reloadInfo);
  dialog.dialog('option', 'addIssueInfo', addIssueInfo);

  // Switch issue tracker tab
  dialog.find('#issue_tracker_id').change(function (event) {
    dialog.find('div[id^="issue-tracker-"]').filter(function () {
      return jQ(this).css('display') === 'block';
    }).toggle();

    let tabIdToShow = jQ('#issue_tracker_id option:selected').data('tab');
    dialog.find('#' + tabIdToShow).toggle();
  });

  dialog.dialog('open');
};


Nitrate.TestRuns.Details.on_load = function() {

  let addIssueDialog = new AddIssueDialog();

  // Observe the interface buttons
  if (jQ('#id_sort').length) {
    jQ('#id_sort').on('click', taggleSortCaseRun);
  }

  jQ('#id_check_all_button').on('click', function(e) {
    toggleAllCheckBoxes(this, 'id_table_cases', 'case_run');
  });

  Nitrate.Utils.enableShiftSelectOnCheckbox('caserun_selector');

  if (jQ('#id_check_box_highlight').attr('checked')) {
    jQ('.mine').addClass('highlight');
  }

  jQ('#id_check_box_highlight').on('click', function(e) {
    e = jQ('.mine');
    if (this.checked) {
      e.addClass('highlight');
    } else {
      e.removeClass('highlight');
    }
  });

  jQ('#id_blind_all_link').on('click', function(e) {
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
        this.title = "Collapse all cases";
        blinddownAllCases(element[0]);
      } else {
        this.title = "Expand all cases";
        blindupAllCases(element[0]);
      }
    }
  });

  // Observe the case run toggle and the comment form
  jQ('.expandable').on('click', function (e) {
    let c = jQ(this).parent(); // Case run row
    let c_container = c.next(); // Next row to show case run details
    let case_id = c.find('input[name="case"]')[0].value;

    let callback = function(t) {
      // Observe the update case run status/comment form
      c_container.parent().find('.update_form').off('submit').on('submit', updateCaseRunStatus);

      c_container.parent().find('.form_comment').off('submit').on('submit', function (e) {
        e.stopPropagation();
        e.preventDefault();
        if (!window.confirm(default_messages.confirm.remove_comment)) {
          return false;
        }
        removeComment(this, function () {
          constructCaseRunZone(c_container[0], c[0], case_id);
        });
      });

      c_container.find('.js-status-button').on('click', function() {
        this.form.value.value = jQ(this).data('formvalue');
      });
      c_container.find('.js-show-comments').on('click', function() {
        toggleDiv(this, jQ(this).data('param'));
      });
      c_container.find('.js-show-changelog').on('click', function() {
        toggleDiv(this, jQ(this).data('param'));
      });
      c_container.find('.js-add-caserun-issue').on('click', function() {
        addIssueDialog.open(jQ(this).data('params'), {
          caseRunRow: c[0],
          caseRunDetailRow: c_container[0]
        });
      });
      c_container.find('.js-remove-caserun-issue').on('click', function(){
        removeIssueFromCaseRuns(jQ(this).data('params'), {
          caseRunRow: c[0],
          caseRunDetailRow: c_container[0]
        });
      });
      c_container.find('.js-add-testlog').on('click', function(){
        let params = jQ(this).data('params');
        addLinkToCaseRun(this, params[0], params[1]);
      });
      c_container.find('.js-remove-testlog').on('click', function(){
        removeLink(this, window.parseInt(jQ(this).data('param')));
      });
    };

    let caseRunId = c.find('input[name="case_run"]')[0].value;
    let caseTextVersion = c.find('input[name="case_text_version"]')[0].value;

    toggleTestCaseRunPane({
      'callback': callback,
      'caseId': case_id,
      'caserunId': caseRunId,
      'caseTextVersion': caseTextVersion,
      'caserunRowContainer': c,
      'expandPaneContainer': c_container
    });
  });

  // Auto show the case run contents.
  if (window.location.hash !== '') {
    fireEvent(jQ('a[href=\"' + window.location.hash + '\"]')[0], 'click');
  }

  // Filter Case-Run
  if (jQ('#filter_case_run').length) {
    jQ('#filter_case_run').on('click',function(e){
      if (jQ('#id_filter').is(':hidden')){
        jQ('#id_filter').show();
        jQ(this).html(default_messages.link.hide_filter);
      } else {
        jQ('#id_filter').hide();
        jQ(this).html(default_messages.link.show_filter);
      }
    });
  }
  //bind click to status btn
  jQ('.btn_status').on('click', function() {
    let from = jQ(this).siblings('.btn_status:disabled')[0].title;
    let to = this.title;
    if (jQ('span#' + to + ' a').text() === '0') {
      let htmlstr = "[<a href='javascript:void(0)' " +
                    "onclick=\"showCaseRunsWithSelectedStatus(jQ('#id_filter')[0], '" +
                    jQ(this).attr('crs_id') +
                    "')\">0</a>]";
      jQ('span#' + to).html(htmlstr);
    }
    if (jQ('span#' + from + ' a').text() === '1') {
      jQ('span#' + from).html("[<a>1</a>]");
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
    jQ('div.progress-inner').attr('style', 'width:' + completePercent + '%');
    jQ('div.progress-failed').attr('style', 'width:' + failedPercent + '%');
  });

  jQ('#btn_edit').on('click', function() {
    let params = jQ(this).data('params');
    window.location.href = params[0] + '?from_plan=' + params[1];
  });
  jQ('#btn_clone').on('click', function() {
    postToURL(jQ(this).data('param'), getSelectedCaseRunIDs());
  });
  jQ('#btn_delete').on('click', function() {
    window.location.href = jQ(this).data('param');
  });
  jQ('#btn_export_csv').on('click', function() {
    window.location.href = jQ(this).data('param') + '?format=csv&' + jQ('#id_form_case_runs').serialize();
  });
  jQ('#btn_export_xml').on('click', function() {
    window.location.href = jQ(this).data('param') + '?format=xml&' + jQ('#id_form_case_runs').serialize();
  });
  jQ('.js-remove-tag').on('click', function() {
    let params = jQ(this).data('params');
    removeRuntag(jQ('.js-tag-ul')[0], params[0], params[1]);
  });
  jQ('.js-add-tag').on('click', function() {
    addRunTag(jQ('.js-tag-ul')[0], jQ(this).data('param'));
  });
  jQ('.js-set-running').on('click', function() {
    window.location.href = jQ(this).data('param') + '?finished=0';
  });
  jQ('.js-set-finished').on('click', function() {
    window.location.href = jQ(this).data('param') + '?finished=1';
  });
  jQ('.js-del-case').on('click', function() {
    delCaseRun(jQ(this).data('param'));
  });
  jQ('.js-update-case').on('click', function() {
    postToURL(jQ(this).data('param'), getSelectedCaseRunIDs());
  });
  jQ('.js-change-assignee').on('click', function() {
    changeCaseRunAssignee();
  });
  jQ('.js-add-issues').on('click', addIssueToBatchCaseRunsHandler);
  jQ('.js-remove-issues').on('click', removeIssueFromBatchCaseRunsHandler);
  jQ('.js-show-commentdialog').on('click', function() {
    showCommentForm();
  });
  jQ('.js-add-cc').on('click', function() {
    addRunCC(jQ(this).data('param'), jQ('.js-cc-ul')[0]);
  });
  jQ('.js-remove-cc').on('click', function() {
    let params = jQ(this).data('params');
    removeRunCC(params[0], params[1], jQ('.js-cc-ul')[0]);
  });
  jQ('.js-add-property').on('click', function() {
    let params = jQ(this).data('params');
    addProperty(params[0], params[1]);
  });
  jQ('.js-edit-property').on('click', function() {
    let params = jQ(this).data('params');
    editValue(jQ(this).parents('form.js-run-env')[0], params[0], params[1], params[2]);
  });
  jQ('.js-remove-property').on('click', function() {
    removeProperty(jQ(this).data('param'), this);
  });
  jQ('.js-env-submit').on('click', function() {
    let params = jQ(this).data('params');
    submitValue(params[0],params[1],params[2], jQ(this).prev()[0], params[3]);
  });
  jQ('.js-caserun-total').on('click', function() {
    showCaseRunsWithSelectedStatus(jQ('#id_filter')[0], '');
  });
  jQ('.js-status-subtotal').on('click', function() {
    showCaseRunsWithSelectedStatus(jQ('#id_filter')[0], jQ(this).data('param'));
  });
  jQ('.js-change-order').on('click', function() {
    let params = jQ(this).data('params');
    changeCaseRunOrder(params[0], params[1], params[2]);
  });
};

Nitrate.TestRuns.New.on_load = function() {
  if (jQ('#testcases').length) {
    jQ('#testcases').dataTable({ "bPaginate": false, "bFilter": false, "bProcessing": true });
  }

  jQ('#add_id_product_version, #add_id_build').on('click', function() {
    return popupAddAnotherWindow(this, 'product');
  });
  jQ('.js-cancel-button').on('click', function() {
    window.history.go(-1);
  });
  jQ('.js-case-summary').on('click', function() {
    toggleTestCaseContents(jQ(this).data('param'));
  });
  jQ('.js-remove-case').on('click', function() {
    let params = jQ(this).data('params');
    removeItem(params[0], params[1]);
  });
};

Nitrate.TestRuns.Edit.on_load = function() {
  bind_version_selector_to_product(false);
  bind_build_selector_to_product(false);
  if (jQ('#id_auto_update_run_status').attr('checked')) {
    jQ('#id_finished').attr({'checked': false, 'disabled': true});
  }
  jQ('#id_auto_update_run_status').on('click', function(){
    if (jQ('#id_auto_update_run_status').attr('checked')) {
      jQ('#id_finished').attr({'checked': false, 'disabled': true});
    } else {
      if (jQ('#id_finished').attr('disabled')) {
        jQ('#id_finished').attr('disabled', false);
      }
    }
  });
  jQ('#add_id_product_version, #add_id_build').on('click', function() {
    return popupAddAnotherWindow(this, 'product');
  });
};

Nitrate.TestRuns.Clone.on_load = function() {
  bind_version_selector_to_product(false);
  bind_build_selector_to_product(false);
  jQ("input[type=checkbox][name^=select_property_id_]").each(function() {
    $this = jQ(this);
    $this.on('click', function(){
      let parent = jQ(this).parent();
      if (this.checked) {
        jQ('select', parent).attr("disabled", false);
        jQ('input[type=hidden]', parent).attr("disabled", false);
      } else {
        jQ('select', parent).attr("disabled", true);
        jQ('input[type=hidden]', parent).attr("disabled", true);
      }
    });
  });

  jQ('#add_id_product_version, #add_id_build').on('click', function() {
    return popupAddAnotherWindow(this, 'product');
  });
  jQ('.js-cancel-button').on('click', function() {
    window.history.go(-1);
  });
  jQ('.js-remove-button').on('click', function() {
    jQ(this).parents('.js-one-case').remove();
  });
};

Nitrate.TestRuns.ChooseRuns.on_load = function() {
  if (jQ('#id_check_all_button').length) {
    jQ('#id_check_all_button').on('click', function(m) {
      toggleAllCheckBoxes(this, 'id_table_runs', 'run');
    });
  }
  jQ('.js-update-button').on('click', function() {
    insertCasesIntoTestRun();
  });
  jQ('.js-help-info').on('click', function() {
    jQ('#help_assign').show();
  });
  jQ('.js-close-help').on('click', function() {
    jQ('#help_assign').hide();
  });
  jQ('.js-toggle-button').on('click', function() {
    let c = jQ(this).parents('.js-one-case');
    let c_container = c.next();
    let case_id = c.find('input[name="case"]').val();
    toggleTestCasePane({ 'case_id': case_id, 'casePaneContainer': c_container }, function() {
      c_container.children().attr('colspan', 9);
    });
    toggleExpandArrow({ 'caseRowContainer': c, 'expandPaneContainer': c_container });
  });
};

Nitrate.TestRuns.AssignCase.on_load = function() {
  if (jQ('#id_check_all_button').length) {
    jQ('#id_check_all_button').on('click', function(m) {
      toggleAllCheckBoxes(this, 'id_table_cases', 'case');
    });
  }

  jQ('input[name="case"]').on('click', function(t) {
    if (this.checked) {
      jQ(this).closest('tr').addClass('selection_row');
      jQ(this).parent().siblings().eq(7).html('<div class="apply_icon"></div>');
    } else {
      jQ(this).closest('tr').removeClass('selection_row');
      jQ(this).parent().siblings().eq(7).html('');
    }
  });

  jQ('.js-how-assign-case').on('click', function() {
    jQ('#help_assign').show();
  });
  jQ('.js-close-how-assign').on('click', function() {
    jQ('#help_assign').hide();
  });
  jQ('.js-toggle-button, .js-case-summary').on('click', function() {
    toggleTestCaseContents(jQ(this).data('param'));
  });
};

/**
 * A callback called after a comment is added to a case run or a case run status is updated with a
 * short comment.
 * @callback
 */
function updateCaseRunDetailAfterCommentIsAdded(caseRunRow, expandedCaseRunDetailRow, caseRunStatusId) {
  // Update the contents
  if (caseRunStatusId !== '') {
    // Update the case run status icon
    let crs = Nitrate.TestRuns.CaseRunStatus;
    caseRunRow.find('.icon_status').each(function(index) {
      for (let i in crs) {
        if (typeof crs[i] === 'string' && jQ(this).is('.btn_' + crs[i])) {
          jQ(this).removeClass('btn_' + crs[i]);
        }
      }
      jQ(this).addClass('btn_' + Nitrate.TestRuns.CaseRunStatus[parseInt(caseRunStatusId) - 1]);
    });

    // Update related people
    caseRunRow.find('.link_tested_by').each(function(i) {
      this.href = 'mailto:' + Nitrate.User.email;
      jQ(this).html(Nitrate.User.username);
    });
  }

  // Mark the case run to mine
  if (!caseRunRow.is('.mine')) {
    caseRunRow.addClass('mine');
  }

  // Blind down next case
  let expandableElem = caseRunRow.find('.expandable')[0];
  fireEvent(expandableElem, 'click');
  if (jQ('#id_check_box_auto_blinddown').attr('checked') && caseRunStatusId !== '') {
    let next_title = expandedCaseRunDetailRow.next();
    if (!next_title.length) {
      return false;
    }
    if (next_title.next().is(':hidden')) {
      fireEvent(next_title.find('.expandable')[0], 'click');
    }
  } else {
    fireEvent(expandableElem, 'click');
  }
}

/**
 * A function registered to the form submit event, from where to add comment to or change status for a case run.
 * @callback
 * @param e
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
    let ajax_loading = getAjaxLoading();
    ajax_loading.id = 'id_loading_' + formData.case_id;
    caseRunDetailCell.html(ajax_loading);
    if (caseRunStatusId !== '') {
      submitComment(jQ('<div>')[0], formData);
    } else {
      submitComment(jQ('<div>')[0], formData, function () {
        updateCaseRunDetailAfterCommentIsAdded(caseRunRow, expandedCaseRunDetailRow, caseRunStatusId);
      });
    }
  }

  // Update the object when changing the status
  if (caseRunStatusId !== '') {
    // Reset the content to loading
    let ajax_loading = getAjaxLoading();
    ajax_loading.id = 'id_loading_' + formData.case_id;
    caseRunDetailCell.html(ajax_loading);

    updateRunStatus(
      formData.content_type, formData.object_pk, formData.field, caseRunStatusId, 'int',
      function () {
        updateCaseRunDetailAfterCommentIsAdded(caseRunRow, expandedCaseRunDetailRow, caseRunStatusId);
      });
  }
}

function changeCaseRunOrder(run_id, case_run_id, sort_key) {
  let nsk = window.prompt('Enter your new order number', sort_key); // New sort key

  if (!nsk) {
    return false;
  }

  if (isNaN(nsk)) {
    window.alert('The value must be a integer number and limit between 0 to 32300.');
    return false;
  }

  if (nsk > 32300 || nsk < 0) {
    window.alert('The value must be a integer number and limit between 0 to 32300.');
    return false;
  }

  if (nsk === sort_key) {
    window.alert('Nothing changed');
    return false;
  }

  updateObject('testruns.testcaserun', case_run_id, 'sortkey', nsk, 'int');
}

function taggleSortCaseRun(event) {
  if (event.target.innerHTML !== 'Done Sorting') {
    jQ('#id_blind_all_link').remove(); // Remove blind all link

    // Remove case text
    jQ('#id_table_cases .hide').remove();

    // Remove blind down arrow link
    jQ('#id_table_cases .blind_icon').remove();

    // Use the title to replace the blind down title link
    jQ('#id_table_cases .blind_title_link').each(function(index) {
      jQ(this).replaceWith((jQ('<span>')).html(this.innerHTML));
    });

    // Use the sortkey content to replace change sort key link
    jQ('#id_table_cases .mark').each(function(index) {
      jQ(this).parent().html(this.innerHTML);
    });

    jQ('#id_table_cases .case_content').remove();
    jQ('#id_table_cases .expandable').unbind();

    // init the tableDnD object
    let table = document.getElementById('id_table_cases');
    let tableDnD = new TableDnD();
    tableDnD.init(table);
    jQ('#id_sort').html('Done Sorting');
  } else {
    jQ('#id_table_cases input[type=checkbox]').attr({ 'checked': true, 'disabled': false });
    postToURL('ordercaserun/', getSelectedCaseRunIDs());
  }
}

function constructCaseRunZone(container, title_container, case_id) {
  let link = jQ(title_container).find('.expandable')[0];
  if (container) {
    let td = jQ('<td>', {'id': 'id_loading_' + case_id, 'colspan': 12});
    td.html(getAjaxLoading());
    jQ(container).html(td);
  }

  if (title_container) {
    fireEvent(link, 'click');
    fireEvent(link, 'click');
  }
}


function removeIssueFromCaseRuns(removeIssueInfo, reloadInfo) {
  if (removeIssueInfo.issueKey === undefined || removeIssueInfo.issueKey === '')
    throw new Error('Missing issue key to remove.');

  getRequest({
    url: '/run/' + removeIssueInfo.runId + '/issues/',
    data: {
      a: 'remove',
      case_run: removeIssueInfo.caseRunIds,
      issue_key: removeIssueInfo.issueKey
    },
    traditional: true,
    success: function(data) {
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


function delCaseRun(run_id) {
  let caseruns = getSelectedCaseRunIDs();
  let numCaseRuns = caseruns.case_run.length;
  if (window.confirm('You are about to delete ' + numCaseRuns + ' case run(s). Are you sure?')) {
    postToURL('removecaserun/', caseruns);
  }
}

function editValue(form, hidebox, selectid, submitid) {
  jQ('#' + hidebox).hide();
  jQ('#' + selectid).show();
  jQ('#' + submitid).show();

  let data = Nitrate.Utils.formSerialize(form);
  let env_property_id = data.env_property_id;

  getRequest({
    url: '/management/getinfo/',
    data: {info_type: 'env_values', env_property_id: env_property_id},
    errorMessage: 'Update values failed',
    success: function(data) {
      let current_value = jQ("input[type=hidden][name=current_run_env]:eq(0)", form);
      let excludeValues = [];

      jQ("input[type=hidden][name=current_run_env]").each(function(index, element) {
        if (element.value !== current_value.val()) {
          excludeValues.push(window.parseInt(element.value));
        }
        return true;
      });

      let values = [];
      jQ.each(data, function(index, value) {
        if (jQ.inArray(value.pk, excludeValues) < 0) {
          values.push([value.pk, value.fields.value]);
        }
        return true;
      });

      setUpChoices(jQ('#' + selectid)[0], values, false);
    },
  });
}

function submitValue(run_id, value, hidebox, select_field, submitid) {
  let new_value = select_field.options[select_field.selectedIndex].innerHTML;
  let old_value = jQ(select_field).prev().prev().val();

  let dup_values = [];
  jQ("input[type=hidden][name=current_run_env]").each(function(index, element) {
    if (element.value !== old_value) {
        dup_values.push(element.value);
    }
    return true;
  });
  if (jQ.inArray(select_field.value, dup_values) >= 0) {
    window.alert("The value is exist for this run");
    return false;
  }

  getRequest({
    url: '/runs/env_value/',
    data: {
      a: 'change',
      old_env_value_id: old_value,
      new_env_value_id: select_field.value,
      run_id: run_id
    },
    success: function(data) {
      jQ('#' + hidebox).html(new_value).show();
      jQ(select_field).hide();
      jQ('#' + submitid).hide();
      jQ(select_field).prev().prev().val(select_field.value);
    },
  });
}

function removeProperty(run_id, element) {
  if (!window.confirm('Are you sure to remove this porperty?')) {
    return false;
  }

  let parent = jQ(element).closest("form");
  let emptySelf = jQ(element).closest("li");
  let env_value_id = jQ("input[type=hidden][name=current_run_env]", parent).get(0).value;

  getRequest({
    url: '/runs/env_value/',
    data: {
      a: 'remove',
      info_type: 'env_values',
      env_value_id: env_value_id,
      run_id: run_id
    },
    errorMessage: 'Edit value failed',
    success: function(data) { emptySelf.remove(); },
  });
}

/**
 * Add a property and one of its values to a test run.
 * @param {number} run_id
 * @param {number} env_group_id
 */
function addProperty(run_id, env_group_id) {
  let template = Handlebars.compile(jQ('#add_property_template').html());
  jQ('#dialog').html(template())
    .find('.js-close-button, .js-cancel-button').on('click', function() {
      jQ('#dialog').hide();
    })
    .end().show();


  getRequest({
    url: '/management/getinfo/',
    data: {info_type: 'env_properties', env_group_id: env_group_id},
    errorMessage: 'Update properties failed',
    success: function (data) {
      setUpChoices(
        jQ('#id_add_env_property')[0],
        data.map(function(o) {return [o.pk, o.fields.name];}),
        false);
    },
  });

  jQ('#id_add_env_property').on('change', function(e) {
    change_value(jQ('#id_add_env_property').val(), 'id_add_env_value');
  });

  jQ('#id_env_add').on('click',function(e) {
    add_property_to_env(run_id, jQ('#id_add_env_value').val());
  });
}

function change_value(env_property_id, selectid) {
  getRequest({
    url: '/management/getinfo/',
    data: {info_type: 'env_values', env_property_id: env_property_id},
    errorMessage: 'Update values failed',
    success: function (data) {
      setUpChoices(
        jQ('#' + selectid)[0],
        data.map(function(o) {return [o.pk, o.fields.value];}),
        0);
    },
  });
}

function add_property_to_env(run_id, env_value_id) {
  getRequest({
    url: '/runs/env_value/',
    data: {
      a: 'add',
      info_type: 'env_values',
      env_value_id: env_value_id,
      run_id: run_id
    },
    success: function(data) {
      jQ('#dialog').hide();
      jQ("#env_area").html(data.fragment);
      jQ('.js-edit-property').on('click', function() {
        let params = jQ(this).data('params');
        editValue(jQ(this).parents('form.js-run-env')[0], params[0], params[1], params[2]);
      });
      jQ('.js-remove-property').on('click', function() {
        removeProperty(jQ(this).data('param'), this);
      });
      jQ('.js-env-submit').on('click', function() {
        let params = jQ(this).data('params');
        submitValue(params[0], params[1], params[2], jQ(this).prev()[0], params[3]);
      });
    },
  });
}

function addRunTag(container, run_id) {
  if (! window.prompt('Please type new tag.')) {
    return false;
  }

  // FIXME: should be a POST request
  sendHTMLRequest({
    url: '/management/tags/',
    data: {a: 'add', run: run_id, tags: tag},
    container: container,
    callbackAfterFillIn: function () {
      jQ('.js-remove-tag').on('click', function() {
        let params = jQ(this).data('params');
        removeRuntag(jQ('.js-tag-ul')[0], params[0], params[1]);
      });
    }
  });
}

function removeRuntag(container, run_id, tag) {
  // FIXME: should be a POST request
  sendHTMLRequest({
    url: '/management/tags/',
    data: {a: remove, run: run_id, tags: tag},
    container: container,
    callbackAfterFillIn: function () {
      jQ('.js-remove-tag').on('click', function() {
        let params = jQ(this).data('params');
        removeRuntag(jQ('.js-tag-ul')[0], params[0], params[1]);
      });
    }
  });
}

function constructRunCC(container, run_id, parameters) {
  sendHTMLRequest({
    url: '/run/' + run_id + '/cc/',
    data: parameters,
    container: container,
    callbackAfterFillIn: function() {
      jQ('.js-remove-cc').on('click', function() {
        let params = jQ(this).data('params');
        removeRunCC(params[0], params[1], jQ('.js-cc-ul')[0]);
      });
      if (jQ('#message').length) {
        window.alert(jQ('#message').html());
        return false;
      }
    }
  });
}

function addRunCC(run_id, container) {
  let user = window.prompt('Please type new email or username for CC.');
  if (!user) {
    return false;
  }
  constructRunCC(container, run_id, {'do': 'add', 'user': user});
}

function removeRunCC(run_id, user, container) {
  if (! window.confirm('Are you sure to delete this user from CC?')) {
    return false;
  }
  constructRunCC(container, run_id, {'do': 'remove', 'user': user});
}

function changeCaseRunAssignee() {
  let selectedCaseRunIDs = getSelectedCaseRunIDs().case_run;
  if (!selectedCaseRunIDs.length) {
    window.alert(default_messages.alert.no_case_selected);
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
        window.alert('Nothing found in database');
        return false;
      }

      if (data.length > 1) {
        window.alert('Multiple instances reached, please define the condition more clear.');
        return false;
      }

      updateObject('testruns.testcaserun', selectedCaseRunIDs, 'assignee', data[0].pk, 'str');
    },
  });
}

/**
 * Retrieve and return selected case run IDs from the container table whose id is id_table_cases.
 * @returns {{case_run: *}}
 */
function getSelectedCaseRunIDs() {
  return {
    case_run:
      jQ('#id_table_cases input[name="case_run"]:checked')
        .map(function () {return this.value;})
        .get()
  }
}

function sortCaseRun(form, order) {
  if (form.order_by.value === order) {
    form.order_by.value = '-' + order;
  } else {
    form.order_by.value = order;
  }
  fireEvent(jQ(form).find('input[type="submit"]')[0], 'click');
}

function showCaseRunsWithSelectedStatus(form, status_id) {
  form.case_run_status__pk.value = status_id;
  fireEvent(jQ(form).find('input[type="submit"]')[0], 'click');
}

//Added for choose runs and add cases to those runs
function serializeRunsFromInputList(table) {
  let elements = jQ('#' + table).parent().find('input[name="run"]:checked');
  let case_ids = [];
  elements.each(function() {
    if (typeof this.value === 'string') {
      case_ids.push(this.value);
    }
  });
  return case_ids;
}

function insertCasesIntoTestRun() {
  if (! window.confirm("Are you sure to add cases to the run?")) {
    return false;
  }

  let case_ids = [];
  jQ('[name="case"]').each(function(i) {
    case_ids.push(this.value);
  });

  postToURL(
    '../chooseruns/',
    {
      testrun_ids: serializeRunsFromInputList("id_table_runs"),
      case_ids: case_ids
    },
    'POST');
}


/*
 * Click event handler for A .js-add-issues
 */
function addIssueToBatchCaseRunsHandler() {
  let caseRunIds =
    getSelectedCaseRunIDs()
      .case_run.map(function (item) {return parseInt(item);});
  if (caseRunIds.length === 0) {
    window.alert(default_messages.alert.no_case_selected);
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
  let caseRunIds =
    getSelectedCaseRunIDs()
      .case_run.map(function (item) {return parseInt(item);});

  if (caseRunIds.length === 0) {
    window.alert(default_messages.alert.no_case_selected);
  } else {
    let reloadInfo = jQ(this).data('reloadInfo');
    let removeIssueInfo = jQ(this).data('removeIssueInfo');
    removeIssueInfo.caseRunIds = caseRunIds;

    let removeIssueDialog = jQ('div[id=showDialog]').dialog({
      title: 'Remove issue key',
      modal: true,
      resizable: false,
      buttons: {
        Ok: function() {
          // Don't care about closing or destroying current dialog.
          // Whole page will be reloaded.
          removeIssueInfo.issueKey = jQ(this).find('input[id=issueKeyToRemove]').val();
          removeIssueFromCaseRuns(removeIssueInfo, reloadInfo);
        },
        Cancel: function() {
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
  let dialog = getDialog();
  let runs = getSelectedCaseRunIDs().case_run;
  if (!runs.length) {
    return window.alert(default_messages.alert.no_case_selected);
  }
  let template = Handlebars.compile(jQ("#batch_add_comment_to_caseruns_template").html());
  jQ(dialog).html(template());

  let commentText = jQ('#commentText');
  let commentsErr = jQ('#commentsErr');
  jQ('#btnComment').on('click', function() {
    let error;
    let comments = jQ.trim(commentText.val());
    if (!comments) {
      error = 'No comments given.';
    }
    if (error) {
      commentsErr.html(error);
      return false;
    }
    postRequest({
      url: '/caserun/comment-many/',
      data: {comment: comments, run: runs},
      traditional: true,
    });
  });
  jQ('#btnCancelComment').on('click', function(){
    jQ(dialog).hide();
    commentText.val('');
  });
  jQ(dialog).show();
}

jQ(document).ready(function(){
  jQ('.btnBlueCaserun').mouseover(function() {
    jQ(this).find('ul').show();
  }).mouseout(function() {
    jQ(this).find('ul').hide();
  });
  jQ('ul.statusOptions a').click(function() {
    let option = jQ(this).attr('value');
    if (option === '') {
      return false;
    }
    let object_pks = getSelectedCaseRunIDs().case_run;
    if (!object_pks.length) {
      window.alert(default_messages.alert.no_case_selected);
      return false;
    }
    if (!window.confirm(default_messages.confirm.change_case_status)) {
      return false;
    }
    updateObject('testruns.testcaserun', object_pks, 'case_run_status', option, 'int');
  });
});

function get_addlink_dialog() {
  return jQ('#addlink_dialog');
}

/**
 * Do AJAX request to backend to remove a link
 *
 * @param sender:
 * @param {number} link_id - the ID of an arbitrary link.
 */
function removeLink(sender, link_id) {
  let url = '/linkref/remove/' + link_id + '/';
  postRequest({url: url, success: function() {
    let li_node = sender.parentNode;
    li_node.parentNode.removeChild(li_node);
  }});
}

/**
 * Add link to case run
 *
 * @param sender - the Add link button, which is pressed to fire this event.
 * @param {number} case_id
 * @param {number} case_run_id
 */
function addLinkToCaseRun(sender, case_id, case_run_id) {
  let dialog_p = get_addlink_dialog();

  dialog_p.dialog('option', 'target_id', case_run_id);
  // These two options are used for reloading TestCaseRun when successfully.
  let container = jQ(sender).parents('.case_content.hide')[0];
  dialog_p.dialog('option', 'container', container);
  let title_container = jQ(container).prev()[0];
  dialog_p.dialog('option', 'title_container', title_container);
  dialog_p.dialog('option', 'case_id', case_id);
  dialog_p.dialog('open');
}

/**
 * Initialize dialog for getting information about new link, which is attached
 * to an arbitrary instance of TestCaseRun
 *
 * @param link_target - string, the name of Model to whose instance new link will be linked.
 */
function initialize_addlink_dialog(link_target) {
  let dialog_p = get_addlink_dialog();

  dialog_p.dialog({
    autoOpen: false,
    modal: true,
    resizable: false,
    height: 300,
    width: 400,
    open: function() {
      jQ(this).off('submit').on('submit', function (e) {
        e.stopPropagation();
        e.preventDefault();
        jQ(this).dialog('widget').find('span:contains("OK")').click();
      });
    },
    buttons: {
      "OK": function() {
        // TODO: validate name and url
        postRequest({
          url: '/linkref/add/',
          data: {
            name: jQ('#testlog_name').attr('value'),
            url: jQ('#testlog_url').attr('value'),
            target: jQ(this).dialog('option', 'target'),
            target_id: jQ(this).dialog('option', 'target_id')
          },
          success: function() {
            dialog_p.dialog('close');

            // Begin to construct case run area
            constructCaseRunZone(
              dialog_p.dialog('option', 'container'),
              dialog_p.dialog('option', 'title_container'),
              dialog_p.dialog('option', 'case_id')
            );
          },
        });
      },
      "Cancel": function() {
        jQ(this).dialog('close');
      }
    },
    beforeClose: function() {
      // clean name and url for next input
      jQ('#testlog_name').val('');
      jQ('#testlog_url').val('');

      return true;
    },
    // Customize variables
    // Used for adding links to an instance of TestCaseRun
    target: link_target,
    /* ATTENTION: target_id can be determined when open this dialog, and
     * this must be set
     */
    target_id: null
  });
}


/**
 * Toggle TestCaseRun panel to edit a case run in run page.
 *
 * @param {Object} options
 * @param {HTMLElement} options.caserunRowContainer
 * @param {HTMLElement} options.expandPaneContainer
 * @param {number} options.caseId
 * @param {number} options.caserunId
 * @param {number} options.caseTextVersion
 * @param {function} options.callback
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
