/* global CaseDetailExpansion */
/* global RIGHT_ARROW, DOWN_ARROW */

Nitrate.TestPlans = {};
Nitrate.TestPlans.Create = {};
Nitrate.TestPlans.List = {};
Nitrate.TestPlans.AdvancedSearch = {};
Nitrate.TestPlans.Details = {};
Nitrate.TestPlans.Edit = {};
Nitrate.TestPlans.SearchCase = {};
Nitrate.TestPlans.Clone = {};
Nitrate.TestPlans.Attachment = {};

/* eslint no-redeclare:off */
/**
 * Collect selected case IDs from a given container HTML element.
 *
 * @param {HTMLElement} container - could be any container like HTML element from where to find out
 *                                  checked inputs with type checkbox and name case.
 * @returns {string[]} a list of selected case IDs without parsing to integer value.
 */
function getSelectedCaseIDs(container) {
  return jQ(container).find('input[name="case"]:checked').map(function () {
    return jQ(this).val();
  }).get();
}

/**
 * Collect selected case IDs from a given container and submit them to a specific location. The
 * container element should have children HTMLInputElement with type checkbox and name case.
 *
 * @param {string} url - the URL for exporting cases.
 * @param {HTMLElement} container - a container element from where to find out selected case IDs.
 */
function submitSelectedCaseIDs(url, container) {
  let selectedCaseIDs = getSelectedCaseIDs(container);
  if (selectedCaseIDs.length === 0) {
    showModal(defaultMessages.alert.no_case_selected, 'Missig something?');
    return;
  }
  postToURL(url, {case: selectedCaseIDs});
}

Nitrate.TestPlans.TreeView = {
  containerId: 'treeview',

  /**
   * Find and return the element containing this tree view.
   *
   * @returns {HTMLElement} the container element.
   */
  getContainer: function () {
    return document.getElementById(this.containerId);
  },

  /**
   * The tree view container has an element containing current plan id. This
   * function returns the id to be used to operate the tree view.
   *
   * @returns {number} the plan id.
   */
  getCurrentPlanId: function () {
    return parseInt(
      jQ(this.getContainer())
        .find('input[name=plan_id]')
        .prop('value')
    );
  },

  getAncestors: function () {
    return jQ(this.getContainer())
      .find('.js-plans-treeview')
      .jstree(true)
      .get_node(this.getCurrentPlanId())
      .parents
      .filter(function (value) { return value !== '#'; })
      .map(function (value) { return parseInt(value); });
  },

  /**
   * Get descendants of current plan
   *
   * @param {boolean} [direct=false] - whether to get the direct descendant plans.
   * @returns {Array} - an array of found descendant ids.
   */
  getDescendants: function (direct) {
    let result = jQ(this.getContainer())
      .find('.js-plans-treeview')
      .jstree(true)
      .get_node(this.getCurrentPlanId());
    result = direct ? result.children : result.children_d;
    return result.map(function (value) { return parseInt(value); });
  },

  /**
   * Lazy-loading TestPlans TreeView
   *
   * @param {number} planId - load tree view for this plan.
   */
  load: function (planId) {
    let thisView = this
      , treeViewContainer = this.getContainer();

    // An array referencing tree view nodes passed to jstree to render the plans
    // tree view.
    // Two purpose of setting it to null here:
    // 1. for the first time to load the tree view, define the variable to reference the array of
    // nodes to be rendered.
    // 2. for subsequent tree view render, mark the old data is expired and it will reference the
    // new value later (see below).
    thisView.treeViewData = null;

    jQ(treeViewContainer).html('');
    jQ(treeViewContainer).html(constructAjaxLoading());

    sendHTMLRequest({
      url: '/plan/' + planId + '/treeview/',
      container: treeViewContainer,
      callbackAfterFillIn: function (xhr) {
        let planPK = parseInt(document.getElementById('id_tree_container').dataset.planId);

        jQ('#js-change-parent-node').on('click', function () {
          thisView.changeParentPlan(planPK);
        });

        jQ('#js-add-child-node').on('click', function () {
          thisView.addChildPlan(planPK);
        });

        jQ('#js-remove-child-node').on('click', function () {
          thisView.removeChildPlan(planPK);
        });

        jQ('div.js-plans-treeview').jstree({
          core: {
            themes: {
              dots: false,
              icons: false
            },
            data: thisView.treeViewData,
          }
        }).on('ready.jstree', function (e, data) {
          jQ(this).jstree('open_all');

          // A workaround to disable the behavior of selecting a node when click an anchor inside
          // the node.
          jQ(this).off('click.jstree', '.jstree-anchor');

          jQ(this).on('click', 'a.js-open-cases-tab', function () {
            Nitrate.TestPlans.Details.openTab('#testcases');
          });

          jQ(this).on('click', 'a.js-open-runs-tab', function () {
            Nitrate.TestPlans.Details.openTab('#testruns');
          });

          let currentPlanId = thisView.getCurrentPlanId();

          jQ(treeViewContainer).find('#js-remove-child-node')[0].disabled =
            jQ(this).jstree(true).get_node(currentPlanId).children.length === 0;
        });
      }
    });
  },

  /**
   * Add child plans to a specific test plan
   *
   * @param {number} currentPlanId - the parent plan of the children.
   */
  addChildPlan: function (currentPlanId) {
    let inputChildPlanIds = window
      .prompt('Enter a comma separated list of plan IDs')
      .replace(/^[,\s]+|[,\s]+$/g, '')
      .split(/[,\s]+/)
      .filter(function (elem) { return elem.length > 0 });

    if (inputChildPlanIds.length === 0) {
      return;
    }

    let thisView = this;
    let descendants = this.getDescendants();

    for (let i = 0; i < inputChildPlanIds.length; i++) {
      let item = inputChildPlanIds[i];
      if (!/^\d+$/.test(item)) {
        showModal(
          'Plan id ' + item + ' is not a number. ', 'Add child plan'
        );
        return;
      }
      if (descendants.indexOf(parseInt(item)) >= 0) {
        showModal('Plan ' + item + ' has been a descendant already.');
        return;
      }
    }

    previewPlan({pk__in: inputChildPlanIds.join(',')}, '', function (e) {
      e.stopPropagation();
      e.preventDefault();

      clearDialog();  // Close the preview dialog

      postRequest({
        url: '/plan/' + currentPlanId + '/treeview/add-children/',
        data: {'children': inputChildPlanIds},
        traditional: true,
        success: function () {
          thisView.load(currentPlanId);
        }
      });
    },
    'This operation will overwrite existing data');
  },

  removeChildPlan: function (currentPlanId) {
    let thisView = this
      , descendants = this.getDescendants();

    let inputChildPlanIds = window
      .prompt('Enter a comma separated list of plan IDs to be removed')
      .replace(/^[,\s]+|[,\s]+$/g, '')
      .split(/[,\s]+/)
      .filter(function (elem) { return elem.length > 0 })
      .filter(function (elem) { return descendants.indexOf(parseInt(elem)) >= 0 });

    if (inputChildPlanIds.length === 0) {
      return;
    }

    previewPlan({pk__in: inputChildPlanIds.join(',')}, '', function (e) {
      e.stopPropagation();
      e.preventDefault();

      // Close the preview dialog
      clearDialog();

      postRequest({
        url: '/plan/' + currentPlanId + '/treeview/remove-children/',
        data: {'children': inputChildPlanIds},
        traditional: true,
        success: function () {
          thisView.load(currentPlanId);
        }
      });
    },
    'This operation will overwrite existing data');
  },

  changeParentPlan: function (currentPlanId) {
    let p = prompt('Enter new parent plan ID');
    if (!p) {
      return false;
    }
    let planId = window.parseInt(p);
    if (isNaN(planId)) {
      showModal('Plan Id should be a numeric. ' + p + ' is invalid.', 'Change parent plan');
      return false;
    }
    if (planId === currentPlanId) {
      showModal('Parent plan should not be the current plan itself.', 'Change parent plan');
      return false;
    }

    let thisView = this;
    let ancestors = thisView.getAncestors();
    if (ancestors.indexOf(planId) >= 0) {
      showModal('Plan ' + planId + ' has been an ancestor already.');
      return;
    }

    previewPlan({plan_id: p}, '', function (e) {
      e.stopPropagation();
      e.preventDefault();

      clearDialog();

      let planId = Nitrate.Utils.formSerialize(this).plan_id;
      updateObject({
        contentType: 'testplans.testplan',
        objectPk: currentPlanId,
        field: 'parent',
        value: planId,
        valueType: 'int',
        callback: function () {
          thisView.load(currentPlanId);
        }
      });
    },
    'This operation will overwrite existing data');
  }
};

Nitrate.TestPlans.Create.on_load = function () {
  registerProductAssociatedObjectUpdaters(
    document.getElementById('id_product'),
    true,
    [
      {
        func: getVersionsByProductId,
        targetElement: document.getElementById('id_product_version'),
        addBlankOption: false
      }
    ]
  );

  jQ('#env_group_help_link').on('click', function () {
    jQ('#env_group_help').toggle();
  });
  jQ('#env_group_help_close').on('click', function () {
    jQ('#env_group_help').hide();
  });
  jQ('#add_id_product').on('click', function () {
    return popupAddAnotherWindow(this);
  });
  jQ('#add_id_product_version').on('click', function () {
    return popupAddAnotherWindow(this, 'product');
  });
  jQ('.js-cancel-button').on('click', function () {
    window.history.back();
  });
};

Nitrate.TestPlans.Edit.on_load = function () {
  registerProductAssociatedObjectUpdaters(
    document.getElementById('id_product'),
    true,
    [
      {
        func: getVersionsByProductId,
        targetElement: document.getElementById('id_product_version'),
        addBlankOption: false
      }
    ]
  );

  jQ('#env_group_help_link').on('click', function () {
    jQ('#env_group_help').toggle();
  });

  jQ('#env_group_help_close').on('click', function () {
    jQ('#env_group_help').hide();
  });

  jQ('.js-back-button').on('click', function () {
    window.location.assign(this.dataset.actionUrl);
  });
};

/**
 * Bind the common actions event handlers on search result, both the advanced
 * search result and the test plans search result.
 */
function bindSearchResultActionEventHandlers() {
  jQ('.js-new-plan').on('click', function () {
    window.location.assign(this.dataset.actionUrl);
  });
  jQ('.js-clone-plans, .js-export-plans, .js-printable-plans').on('click', function () {
    let params = {plan: Nitrate.Utils.formSerialize(this.form).plan};
    postToURL(this.dataset.actionUrl, params, 'get');
  });
}

Nitrate.TestPlans.AdvancedSearch.on_load = function () {
  jQ('#testplans_table :checkbox').on('change', function () {
    let disable = jQ('#testplans_table tbody :checkbox:checked').length === 0;
    jQ('.js-printable-plans').prop('disabled', disable);
    jQ('.js-clone-plans').prop('disabled', disable);
    jQ('.js-export-plans').prop('disabled', disable);
  });

  jQ('#testplans_table tbody tr td:nth-child(1)').shiftcheckbox({
    checkboxSelector: ':checkbox',
    selectAll: '#testplans_table .js-select-all'
  });

  bindSearchResultActionEventHandlers();

  jQ('#testplans_table').dataTable(
    Object.assign({}, Nitrate.TestPlans.SearchResultTableSettings, {
      iDeferLoading: Nitrate.TestPlans.AdvancedSearch.numberOfPlans,
      sAjaxSource: '/advance-search/' + this.window.location.search,
    })
  );
};

Nitrate.TestPlans.SearchResultTableSettings = Object.assign({}, Nitrate.DataTable.commonSettings, {

  // By default, plans are sorted by create_date in desc order.
  // It is equal to set the pk column in the DataTable initialization.
  aaSorting: [[ 1, 'desc' ]],

  oLanguage: {
    sEmptyTable: 'No plans found.'
  },

  aoColumns: [
    {'bSortable': false},     // Selector checkbox
    null,                     // ID
    {'sType': 'html'},        // Name
    {'sType': 'html'},        // Author
    {'sType': 'html'},        // Owner
    null,                     // Product
    null,                     // Type
    null,                     // Cases
    null,                     // Runs
    {'bSortable': false}      // Actions
  ],

  fnDrawCallback: function () {
    jQ('#testplans_table tbody tr td:nth-child(1)').shiftcheckbox({
      checkboxSelector: ':checkbox',
      selectAll: '#testplans_table .js-select-all'
    });

    jQ('#testplans_table :checkbox').on('change', function () {
      let disable = jQ('#testplans_table tbody :checkbox:checked').length === 0;
      jQ('.js-printable-plans').prop('disabled', disable);
      jQ('.js-clone-plans').prop('disabled', disable);
      jQ('.js-export-plans').prop('disabled', disable);
    });
  },

  fnInfoCallback: function (oSettings, iStart, iEnd, iMax, iTotal, sPre) {
    return 'Showing ' + (iEnd - iStart + 1) + ' of ' + iTotal + ' plans';
  }

});

Nitrate.TestPlans.List.on_load = function () {
  registerProductAssociatedObjectUpdaters(
    document.getElementById('id_product'),
    true,
    [
      {
        func: getVersionsByProductId,
        targetElement: document.getElementById('id_product_version'),
        addBlankOption: true
      }
    ]
  );

  if (jQ('#id_check_all_plans').length) {
    jQ('#id_check_all_plans').on('click', function () {
      jQ('.js-printable-plans').prop('disabled', !this.checked);
    });
  }

  jQ('#testplans_table').dataTable(
    Object.assign({}, Nitrate.TestPlans.SearchResultTableSettings, {
      iDeferLoading: this.numberOfPlans,
      sAjaxSource: '/plans/pages/' + this.window.location.search,
    })
  );

  bindSearchResultActionEventHandlers();
};

Nitrate.TestPlans.Details = {
  'tabContentContainerIds': {
    'document': 'document',
    'confirmedCases': 'testcases',
    'reviewingCases': 'reviewcases',
    'attachment': 'attachment',
    'testruns': 'testruns',
    'components': 'components',
    'log': 'log',
    'treeview': 'treeview',
    'tag': 'tag'
  },

  /**
   * Open a specific tab in a plan page
   *
   * @param {string} tabHash - the hash of a specific tab to be opened. For example, #testcases.
   */
  openTab: function (tabHash) {
    jQ('a[href="' + tabHash + '"]').trigger('click');
  },

  'initTabs': function () {
    jQ('li.tab a').on('click', function () {
      jQ('div.tab_list').hide();
      jQ('li.tab').removeClass('tab_focus');
      jQ(this).parent().addClass('tab_focus');
      jQ('#' + this.href.slice(this.href.indexOf('#') + 1)).show();
    });

    // Display the tab indicated by hash along with URL.
    let defaultSwitchTo = '#testcases';
    let switchTo = window.location.hash;
    let exist = jQ('#contentTab')
      .find('a')
      .map(function (index, element) {
        return element.getAttribute('href');
      })
      .filter(function (index, element) {
        return element === switchTo;
      }).length > 0;
    if (!exist) {
      switchTo = defaultSwitchTo;
    }

    this.openTab(switchTo);
  },
  /*
   * Load cases table.
   *
   * Proxy of global function with same name.
   */
  'loadCases': function (container, planId, parameters) {
    constructPlanDetailsCasesZone(container, planId, parameters);

    if (this._bindEventsOnLoadedCases === undefined) {
      this._bindEventsOnLoadedCases = bindEventsOnLoadedCases({
        'cases_container': container,
        'plan_id': planId,
        'parameters': parameters
      });
    }
  },
  // Loading newly created cases with proposal status to show table of these kind of cases.
  'loadConfirmedCases': function (planId) {
    let containerId = 'testcases';
    this.loadCases(containerId, planId, {
      'a': 'initial',
      'template_type': 'case',
      'from_plan': planId
    });
  },
  // Loading reviewing cases to show table of these kind of cases.
  'loadReviewingCases': function (planId) {
    let containerId = 'reviewcases';
    this.loadCases(containerId, planId, {
      'a': 'initial',
      'template_type': 'review_case',
      'from_plan': planId
    });
  },

  'observeEvents': function (planId) {
    // let NTPD = Nitrate.TestPlans.Details;

    let self = this;

    jQ('#tab_testcases').on('click', function () {
      if (!self.testcasesTabOpened) {
        self.loadConfirmedCases(planId);
        self.testcasesTabOpened = true;
      }
    });

    jQ('#tab_treeview').on('click', function () {
      if (!self.plansTreeViewOpened) {
        Nitrate.TestPlans.TreeView.load(planId);
        self.plansTreeViewOpened = true;
      }
    });

    jQ('#tab_reviewcases').on('click', function () {
      if (!self.reviewingCasesTabOpened) {
        self.loadReviewingCases(planId);
        self.reviewingCasesTabOpened = true;
      }
    });

    // Initial the enable/disble btns
    if (jQ('#btn_disable').length) {
      jQ('#btn_disable').on('click', function (){
        updateObject({
          contentType: 'testplans.testplan',
          objectPk: planId,
          field: 'is_active',
          value: 'False',
          valueType: 'bool'
        });
      });
    }

    if (jQ('#btn_enable').length) {
      jQ('#btn_enable').on('click', function () {
        updateObject({
          contentType: 'testplans.testplan',
          objectPk: planId,
          field: 'is_active',
          value: 'True',
          valueType: 'bool'
        });
      });
    }
  },
  'reopenCasesTabThen': function () {
    this.testcasesTabOpened = false;
  },
  'reopenReviewingCasesTabThen': function () {
    this.reviewingCasesTabOpened = false;
  },
  /*
   * Helper function to reopen other tabs.
   *
   * Arguments:
   * - container: a jQuery object, where the operation happens to reopen other tabs. The container
   *              Id is used to select the reopen operations.
   */
  'reopenTabHelper': function (container) {
    let self = this;
    let switchMap = {
      'testcases': function () {
        self.reopenReviewingCasesTabThen();
      },
      'reviewcases': function () {
        self.reopenCasesTabThen();
      }
    };
    switchMap[container.prop('id')]();
  },
  'on_load': function () {
    let planId = Nitrate.TestPlans.Instance.pk;

    // Initial the contents
    constructTagZone(jQ('#tag')[0], {plan: planId});
    constructPlanComponentsZone('components');

    Nitrate.TestPlans.Details.observeEvents(planId);
    Nitrate.TestPlans.Details.initTabs();

    // Make the import case dialog draggable.
    jQ('#id_import_case_zone').draggable({containment: '#content'});

    // Bind for run form
    jQ('#id_form_run').on('submit', function (e) {
      if (!Nitrate.Utils.formSerialize(this).run) {
        e.stopPropagation();
        e.preventDefault();
        showModal(defaultMessages.alert.no_run_selected, 'Missing something?');
      }
    });

    Nitrate.TestPlans.Runs.initializeRunTab();
    Nitrate.TestPlans.Runs.bind();

    jQ('#btn_edit, #btn_clone, #btn_export, #btn_print').on('click', function () {
      window.location.assign(this.dataset.actionUrl);
    });

    jQ('#id_import_case_zone').find('.js-close-zone').on('click', function () {
      jQ('#id_import_case_zone').hide();
      jQ('#import-error').empty();
    });
  }
};

Nitrate.TestPlans.SearchCase.on_load = function () {
  registerProductAssociatedObjectUpdaters(
    document.getElementById('id_product'),
    true,
    [
      {
        func: getCategoriesByProductId,
        targetElement: document.getElementById('id_category'),
        addBlankOption: true
      }
    ]
  );

  // new feature for searching by case id.
  let quickSearch = jQ('#tp_quick_search_cases_form');
  let normalSearch = jQ('#tp_advanced_search_case_form');
  let quickTab = jQ('#quick_tab');
  let normalTab = jQ('#normal_tab');
  let searchMode = jQ('#search_mode');
  let errors = jQ('.errors');

  /* eslint func-style:off */
  let triggerFormDisplay = function (options) {
    options.show.show();
    options.show_tab.addClass('profile_tab_active');
    options.hide.hide();
    options.hide_tab.removeClass('profile_tab_active');
  };

  jQ('#quick_search_cases').on('click', function () {
    // clear errors
    errors.empty();
    searchMode.val('quick');
    triggerFormDisplay({
      'show': quickSearch,
      'show_tab': quickTab,
      'hide': normalSearch,
      'hide_tab': normalTab
    });
  });
  jQ('#advanced_search_cases').on('click', function () {
    // clear errors
    errors.empty();
    searchMode.val('normal');
    triggerFormDisplay({
      'show': normalSearch,
      'show_tab': normalTab,
      'hide': quickSearch,
      'hide_tab': quickTab
    });
  });

  if (jQ('#id_table_cases').length) {
    jQ('#id_table_cases').dataTable(
      Object.assign({}, Nitrate.DataTable.commonSettings, {
        bServerSide: false,

        aaSorting: [[1, 'desc']],
        aoColumnDefs: [
          {'bSortable': false, 'aTargets': ['nosort']}
        ],

        fnDrawCallback: function () {
          jQ('#id_table_cases tbody tr td:nth-child(1)').shiftcheckbox({
            checkboxSelector: ':checkbox',
            selectAll: '#id_table_cases .js-select-all'
          });

          jQ('#id_table_cases :checkbox').on('change', function () {
            let disable = jQ('#id_table_cases tbody :checkbox:checked').length === 0;
            jQ('#add-selected-cases').prop('disabled', disable);
          });
        }
      })
    );
  }
};

Nitrate.TestPlans.Clone.on_load = function () {
  registerProductAssociatedObjectUpdaters(
    document.getElementById('id_product'),
    true,
    [
      {
        func: getVersionsByProductId,
        targetElement: document.getElementById('id_product_version'),
        addBlankOption: false
      }
    ]
  );

  jQ('#id_link_testcases').on('change', function () {
    if (this.checked) {
      this.parentNode.parentNode.className = 'choose';
      jQ('#id_clone_case_zone')[0].style.display = 'block';
    } else {
      this.parentNode.parentNode.className = 'unchoose';
      jQ('#id_clone_case_zone')[0].style.display = 'none';
    }
  });

  jQ('#id_copy_testcases').on('change', function () {
    if (this.checked) {
      jQ('#id_maintain_case_orignal_author')[0].disabled = false;
      jQ('#id_keep_case_default_tester')[0].disabled = false;
    } else {
      jQ('#id_maintain_case_orignal_author')[0].disabled = true;
      jQ('#id_keep_case_default_tester')[0].disabled = true;
    }
  });

  jQ('.js-cancel-button').on('click', function () {
    window.history.back();
  });
};

Nitrate.TestPlans.Attachment.on_load = function () {
  jQ(document).ready(function () {
    jQ('#upload_file').change(function () {
      let iSize = jQ('#upload_file')[0].files[0].size;
      let limit = parseInt(jQ('#upload_file').prop('limit'));

      if (iSize > limit) {
        showModal(
          'Your attachment\'s size is beyond limit, ' +
          'please limit your attachments to under 5 megabytes (MB).',
          'Upload attachment'
        );
      }
    });

    jQ('.js-back-button').on('click', function () {
      window.history.go(-1);
    });
  });
};

function showMoreSummary() {
  jQ('#display_summary').show();
  if (jQ('#display_summary_short').length) {
    jQ('#id_link_show_more').hide();
    jQ('#id_link_show_short').show();
    jQ('#display_summary_short').hide();
  }
}

// Deprecated. Remove when it's unusable any more.
function changeCaseOrder(parameters, callback) {
  let nsk = '';
  if (Object.prototype.hasOwnProperty.call(parameters, 'sortkey')) {
    nsk = window.prompt('Enter your new order number', parameters.sortkey);   // New sort key
    if (parseInt(nsk) === parseInt(parameters.sortkey)) {
      showModal('Nothing changed', 'Change case order');
      return false;
    }
  } else {
    nsk = window.prompt('Enter your new order number');
  }

  if (!nsk) {
    return false;
  }

  if (isNaN(nsk)) {
    showModal(
      'The value must be an integer number and limit between 0 to 32300.',
      'Change case order'
    );
    return false;
  }

  nsk = parseInt(nsk);

  if (nsk > 32300 || nsk < 0) {
    showModal(
      'The value must be a number and limit between 0 to 32300.',
      'Change case order'
    );
    return false;
  }

  updateObject({
    contentType: 'testcases.testcaseplan',
    objectPk: parameters.testcaseplan,
    field: 'sortkey',
    value: nsk,
    valueType: 'int',
    callback: callback
  });
}

function changeTestCaseStatus(planId, selector, caseId, beConfirmed, wasConfirmed) {
  postRequest({
    url: '/ajax/update/case-status/',
    data: {
      from_plan: planId,
      case: caseId,
      target_field: 'case_status',
      new_value: selector.value,
    },
    success: function (data) {
      let caseStatus = '';
      let node = null;
      for (let i = 0; (node = selector.options[i]); i++) {
        if (node.selected) {
          caseStatus = node.innerHTML;
        }
      }

      // container should be got before selector is hidden.
      let curCasesContainer = jQ(selector).parents('.tab_list');

      let label = jQ(selector).prev()[0];
      jQ(label).html(caseStatus).show();
      jQ(selector).hide();

      if (beConfirmed || wasConfirmed) {
        jQ('#run_case_count').text(data.run_case_count);
        jQ('#case_count').text(data.case_count);
        jQ('#review_case_count').text(data.review_case_count);
        jQ('#' + caseId).next().remove();
        jQ('#' + caseId).remove();

        // We have to reload the other side of cases to reflect the status
        // change. This MUST be done before selector is hided.
        Nitrate.TestPlans.Details.reopenTabHelper(curCasesContainer);
      }
    },
  });
}

/**
 * Handle events inside expanded reviewing case details pane
 *
 * @param {jQuery} expandableEventTarget
 *  a jQuery object whose click event is triggered to expand the case.
 * @param {jQuery} expandedCaseDetailsPane
 *  a jQuery object representing the container containing expanded case details.
 * @returns {Function} an event handler to be registered.
 */
function reviewCaseContentCallback(expandableEventTarget, expandedCaseDetailsPane) {
  return function () {
    let commentContainerT = jQ('<div>')[0];

    // Change status/comment callback
    expandedCaseDetailsPane.find('.update_form').unbind('submit').on('submit', function (e) {
      e.stopPropagation();
      e.preventDefault();

      let params = Nitrate.Utils.formSerialize(this);
      submitComment(commentContainerT, params, function () {
        let td = jQ('<td>', {colspan: 12});
        td.append(constructAjaxLoading('id_loading_' + params.object_pk));
        expandedCaseDetailsPane.html(td);
        // FIXME: refresh the content only once
        expandableEventTarget.trigger('click');
        expandableEventTarget.trigger('click');
      });
    });

    // Observe the delete comment form
    expandedCaseDetailsPane.find('.form_comment').off('submit').on('submit', function (e) {
      e.stopPropagation();
      e.preventDefault();

      if (!window.confirm(defaultMessages.confirm.remove_comment)) {
        return false;
      }
      // Every comment form has a hidden input with name object_pk to associate with the case.
      let caseId = Nitrate.Utils.formSerialize(this).object_pk;
      removeComment(this, function () {
        let td = jQ('<td>', {colspan: 12});
        td.append(constructAjaxLoading('id_loading_' + caseId));
        expandedCaseDetailsPane.html(td);
        // FIXME: refresh the content only once.
        expandableEventTarget.trigger('click');
        expandableEventTarget.trigger('click');
      });
    });
  };
}

/**
 * Check whether all cases within confirmed or reviewing cases tab are collapsed.
 *
 * @param {boolean} inReviewingCasesTab - indicate to get the number of reviewing cases, otherwise
 *                                        get the number of confirmed cases.
 * @param {HTMLElement} casesTable - the table containing cases.
 * @returns {boolean} - return true if all expanded case details pane is collapsed, otherwise
 *                      false is returned.
 */
function areAllCasesCollapsed(inReviewingCasesTab, casesTable) {
  let numberContainerId = inReviewingCasesTab ? 'review_case_count' : 'run_case_count'
    , casesCount = parseInt(document.getElementById(numberContainerId).textContent)
    , collapsedCasesCount = jQ(casesTable).find('tr.case_content:hidden').length;
  return casesCount === collapsedCasesCount;
}

/*
 * Bind events on loaded cases.
 *
 * This is a closure. The real function needs cases container, plan's ID, and
 * initial parameters as the initializatio parameters.
 *
 * Arguments:
 * - container: the HTML element containing all loaded cases. Currently, the
 *   container is a TABLE.
 */
function bindEventsOnLoadedCases(options) {
  let parameters = options.parameters;
  let planId = options.plan_id;
  let casesContainer = options.cases_container;

  return function (container, form) {
    // Observe the change sortkey
    jQ(container).parent().find('.case_sortkey.js-just-loaded').on('click', function () {
      changeCaseOrder({'testcaseplan': jQ(this).next().html(), 'sortkey': jQ(this).html()}, function () {
        constructPlanDetailsCasesZone(casesContainer, planId, parameters);
      });
    });

    jQ(container).parent().find('.change_status_selector.js-just-loaded').on('change', function () {
      let beConfirmed = (parseInt(this.value) === 2);
      let wasConfirmed = (jQ(this).parent()[0].attributes.status.value === 'CONFIRMED');
      let caseId = jQ(this).parent().parent()[0].id;
      changeTestCaseStatus(planId, this, caseId, beConfirmed, wasConfirmed);
    });

    // Expand/collapse case details pane
    jQ(container).parent().find('.expandable.js-just-loaded').on('click', function () {
      let btn = this
        , caseDetailRow = jQ(this).parent().next() // Content Containers
        , inReviewingCasesTab = form.type.value === 'review_case';

      new CaseDetailExpansion(this, inReviewingCasesTab).toggle(
        inReviewingCasesTab ? reviewCaseContentCallback(jQ(btn), caseDetailRow) : function () {}
      );

      let iconFile = areAllCasesCollapsed(inReviewingCasesTab, container) ? RIGHT_ARROW : DOWN_ARROW;
      jQ(container).find('img.js-expand-collapse-cases').prop('src', iconFile);
    });

    /*
     * Using class just-loaded to identify thoes cases that are just loaded to
     * avoid register event handler repeatedly.
     */
    jQ(container).parent().find('.js-just-loaded').removeClass('js-just-loaded');
  };
}


/**
 * Serialize form data including the selected cases for AJAX requst.
 * Used in function constructPlanDetailsCasesZone.
 *
 * @param {object} options - options to serialize form data
 * @param {string[]} options.selectedCaseIDs - an array of selected case ids.
 * @param {boolean} [options.hashable=false] - indicate whether to construct and return an object
 *                                             containing the form data.
 * @returns {object|string} - an object containing the serialized form data if options.hashable is
 *                            true, otherwise a string representation will be returned.
 */
function serializeFormData(options) {
  let hashable = options.hashable || false;

  let unhashableData = options.selectedCaseIDs.map(function (caseID) {
    return 'case=' + caseID;
  }).join('&');

  let formData =
    hashable ?
      Nitrate.Utils.formSerialize(options.form) :
      jQ(options.form).serialize();

  if (hashable) {
    let arr = unhashableData.split('&');
    for (let i = 0; i < arr.length; i++) {
      let parts = arr[i].split('=');
      let key = parts[0], value = parts[1];
      // FIXME: not sure how key can be an empty string
      if (!key.length) {
        continue;
      }
      if (key in formData) {
        // Before setting value, the original value must be converted to an array object.
        if (formData[key].push === undefined) {
          formData[key] = [formData[key], value];
        } else {
          formData[key].push(value);
        }
      } else {
        formData[key] = value;
      }
    }
  } else {
    formData += '&' + unhashableData;
  }

  return formData;
}

function changeCaseOrder2(parameters, callback) {
  let nsk = '';
  if (Object.prototype.hasOwnProperty.call(parameters, 'sortkey')) {
    nsk = window.prompt('Enter your new order number', parameters.sortkey);   // New sort key
    if (parseInt(nsk) === parseInt(parameters.sortkey)) {
      showModal('Nothing changed', 'Change case order');
      return false;
    }
  } else {
    nsk = window.prompt('Enter your new order number');
  }

  if (!nsk) {
    return false;
  }

  if (isNaN(nsk)) {
    showModal(
      'The value must be a number and limit between 0 to 32300.',
      'Change case order'
    );
    return false;
  }

  nsk = parseInt(nsk);

  if (nsk > 32300 || nsk < 0) {
    showModal(
      'The value must be an integer number and limit between 0 to 32300.',
      'Change case order'
    );
    return false;
  }

  parameters.target_field = 'sortkey';
  parameters.new_value = nsk;

  postRequest({
    url: '/ajax/update/cases-sortkey/',
    data: parameters,
    traditional: true,
    success: callback
  });
}

/**
 * Load/reload the cases area which contains dropdown menus and controls.
 *
 * @param {string|jQuery} container - the id or jQuery object of the element as
 *                                    container containing the cases area.
 * @param {number} planId - the plan id.
 * @param {object} parameters - information about loading and displaying cases just updated.
 */
function constructPlanDetailsCasesZone(container, planId, parameters) {
  container = typeof container === 'string' ? jQ('#' + container)[0] : container;
  jQ(container).html(constructAjaxLoading());

  const defaultCasesFilter = {a: 'initial', from_plan: planId};
  let postData = parameters || defaultCasesFilter;

  postHTMLRequest({
    url: '/cases/',
    data: postData,
    traditional: true,
    container: container,
    callbackAfterFillIn: function () {
      jQ('.show_change_status_link').on('click', function () {
        jQ(this).hide().next().show();
      });

      let casesTable = jQ(container).find('.js-cases-list')[0]
        , navForm = jQ(container).find('form.js-cases-actions')
        ;

      /**
       * After the action succeeds against selected cases, the whole cases pane has to be reloaded.
       *
       * @param {string} [action=update] - the action assigned to request argument a.
       */
      let reloadCases = function (action) {
        let reloadCasesParams = Nitrate.Utils.formSerialize(navForm[0]);
        reloadCasesParams.case = getSelectedCaseIDs(casesTable);
        reloadCasesParams.a = action || 'update';
        constructPlanDetailsCasesZone(container, planId, reloadCasesParams);
      };

      /**
       * A simple helper function trying to simplify the call of postRequest that just makes a POST
       * request in traditional way of serializing post data and then simply reloads the cases.
       *
       * @param {string} url - send POST request to this URL
       * @param {object} data - the post data
       */
      let postRequestAndReloadCases = function (url, data) {
        postRequest({
          url: url,
          data: jQ.param(data, true),
          success: function () {
            reloadCases();
          }
        });
      };

      // Filter cases
      navForm.on('submit', function (e) {
        e.stopPropagation();
        e.preventDefault();
        constructPlanDetailsCasesZone(container, planId, Nitrate.Utils.formSerialize(navForm[0]));
      });

      jQ(casesTable).find('tbody .selector_cell').shiftcheckbox({
        checkboxSelector: ':checkbox',
        selectAll: jQ(casesTable).find('.js-select-all')
      });

      navForm.find('.js-new-case').on('click', function () {
        window.location.assign(this.dataset.actionUrl);
      });

      navForm.find('.js-import-cases').on('click', function () {
        jQ('#id_import_case_zone').toggle();
      });

      navForm.find('.js-add-case-to-plan').on('click', function () {
        window.location.assign(this.dataset.actionUrl);
      });

      navForm.find('.js-export-cases, .js-print-cases').on('click', function () {
        submitSelectedCaseIDs(this.dataset.actionUrl, casesTable);
      });

      navForm.find('.js-clone-cases').on('click', function () {
        let params = {
          from_plan: planId,
          case: getSelectedCaseIDs(casesTable)
        };
        postToURL(this.dataset.actionUrl, params, 'get');
      });

      navForm.find('.js-remove-cases').on('click', function () {
        let selectedCaseIDs = getSelectedCaseIDs(casesTable);
        if (selectedCaseIDs.length === 0) {
          return;
        }
        if (! confirm('Are you sure you want to remove test case(s) from this test plan?')) {
          return;
        }

        postRequestAndReloadCases('delete-cases/', {case: selectedCaseIDs});
      });

      navForm.find('.js-new-run').on('click', function () {
        let params = {
          from_plan: planId,
          case: getSelectedCaseIDs(casesTable)
        };
        postToURL(this.dataset.actionUrl, params);
      });

      navForm.find('.js-add-case-to-run').on('click', function () {
        let params = {case: getSelectedCaseIDs(casesTable)};
        postToURL(this.dataset.actionUrl, params, 'get');
      });

      navForm.find('.js-status-item').on('click', function () {
        let selectedCaseIDs = getSelectedCaseIDs(casesTable);
        if (selectedCaseIDs.length === 0) {
          showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
          return false;
        }

        let newStatusId = parseInt(this.dataset.statusId);
        confirmDialog({
          message: defaultMessages.confirm.change_case_status,
          title: 'Manage Test Case Status',
          yesFunc: function () {
            postRequest({
              url: '/ajax/update/case-status/',
              data: {
                'from_plan': planId,
                'case': selectedCaseIDs,
                'target_field': 'case_status',
                'new_value': newStatusId
              },
              traditional: true,
              success: function (data) {
                jQ('#run_case_count').text(data.run_case_count);
                jQ('#case_count').text(data.case_count);
                jQ('#review_case_count').text(data.review_case_count);

                reloadCases();

                Nitrate.TestPlans.Details.reopenTabHelper(jQ(container));
              },
            });
          }
        });
      });

      navForm.find('.js-priority-item').on('click', function () {
        let selectedCaseIDs = getSelectedCaseIDs(casesTable);
        if (selectedCaseIDs.length === 0) {
          showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
          return false;
        }

        let newValue = this.dataset.priorityId;

        confirmDialog({
          message: defaultMessages.confirm.change_case_priority,
          title: 'Manage Test Case Priority',
          yesFunc: function () {
            postRequestAndReloadCases('/ajax/update/cases-priority/', {
              from_plan: planId,
              case: selectedCaseIDs,
              target_field: 'priority',
              new_value: newValue
            });
          }
        });
      });

      let allCasesExpanded = false;

      jQ(casesTable).find('img.js-expand-collapse-cases').on('click', function () {
        jQ(casesTable).find('img.js-expand-collapse-case').each(function () {
          let caseTr = jQ(this).parents('tr')
            , caseDetailsTr = caseTr.next();

          if (caseDetailsTr.is(allCasesExpanded ? ':visible' : ':hidden')) {
            jQ(this).trigger('click');
          }
        });

        allCasesExpanded = ! allCasesExpanded;
      });

      if (jQ(casesTable).find('tbody tr:visible').length > 1) {
        // Only make sense to sort rows when there are more than one cases
        jQ(casesTable).find('.js-table-header-sortable').on('click', function () {
          sortCase(container, jQ(this).parents('thead').data('planId'), this.dataset.orderBy);
        });
      }

      // Event handlers common to both cases and reviewing cases tabs

      // Change the case background after selected
      jQ(casesTable).find('tbody :checkbox').on('click', function () {
        let tr = jQ(this).parents('tr')
          , action = this.checked ? tr.addClass : tr.removeClass;
        action('selection_row');
      });

      navForm.find('.btn_filter').on('click', function () {
        let filterContainer = navForm.find('.list_filter');
        if (filterContainer.is(':visible')) {
          filterContainer.hide();
          jQ(this).html(defaultMessages.link.show_filter);
        } else {
          filterContainer.show();
          jQ(this).html(defaultMessages.link.hide_filter);
        }
      });

      // Bind click the tags in tags list to tags field in filter
      navForm.find('.taglist a').on('click', function () {
        let filterContainer = navForm.find('.list_filter');
        if (! filterContainer.is(':visible')) {
          navForm.find('.btn_filter').trigger('click');
        }
        let existingValue = navForm[0].tag__name__in.value.trim();
        if (existingValue.length === 0) {
          navForm[0].tag__name__in.value = this.textContent;
        } else {
          navForm[0].tag__name__in.value = existingValue + ',' + this.textContent;
        }
      });

      // Bind the sort link
      navForm.find('.btn_sort').on('click', function () {
        let params = Nitrate.Utils.formSerialize(navForm[0]);
        params.case = getSelectedCaseIDs(casesTable);
        resortCasesDragAndDrop(container, this, navForm[0], casesTable, params, function () {
          reloadCases('initial');
        });
      });

      navForm.find('input.btn_automated').on('click', function () {
        let selectedCaseIDs = getSelectedCaseIDs(casesTable);
        if (selectedCaseIDs.length === 0) {
          showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
          return;
        }

        let d = jQ('<div>', {'class': 'automated_form'})[0];

        sendHTMLRequest({
          url: Nitrate.http.URLConf.reverse({name: 'get_form'}),
          data: {app_form: 'testcases.CaseAutomatedForm'},
          container: d,
          callbackAfterFillIn: function (xhr) {
            let returntext = xhr.responseText;

            let dialogContainer = getDialog();
            jQ(dialogContainer).html(constructAjaxLoading());
            jQ(dialogContainer).show();

            jQ(dialogContainer).html(
              constructForm(returntext, '/cases/automated/', function (e) {
                e.stopPropagation();
                e.preventDefault();

                let data = Nitrate.Utils.formSerialize(this);
                clearDialog(dialogContainer);

                if (
                  data.o_is_automated === undefined &&
                  data.o_is_manual === undefined &&
                  data.o_is_automated_proposed === undefined
                ) {
                  return true;
                }

                data.a = 'change';
                data.case = selectedCaseIDs;

                postRequestAndReloadCases(
                  Nitrate.http.URLConf.reverse({name: 'cases_automated'}), data
                );
              })
            );
          }
        });
      });

      let updateCasesPeople = function (url, targetField) {
        let selectedCaseIDs = getSelectedCaseIDs(casesTable);
        if (selectedCaseIDs.length === 0) {
          showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
          return false;
        }

        let emailOrUsername = window.prompt('Please type new email or username');
        if (!emailOrUsername) {
          return false;
        }

        postRequestAndReloadCases(url, {
          from_plan: planId,
          case: selectedCaseIDs,
          target_field: targetField,
          new_value: emailOrUsername
        });
      };

      navForm.find('input.btn_default_tester').on('click', function () {
        updateCasesPeople('/ajax/update/cases-default-tester/', 'default_tester');
      });

      navForm.find('input.btn_reviewer').on('click', function () {
        updateCasesPeople('/ajax/update/cases-reviewer/', 'reviewer');
      });

      navForm.find('input.sort_list').on('click', function () {
        // NOTE: new implementation does not use testcaseplan.pk
        let selectedCaseIDs = getSelectedCaseIDs(casesTable);
        if (selectedCaseIDs.length === 0) {
          showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
          return false;
        }

        let postdata = serializeFormData({
          'form': navForm[0],
          'selectedCaseIDs': selectedCaseIDs,
          'hashable': true
        });

        changeCaseOrder2(postdata, function () {
          reloadCases();
        });
      });

      // Observe the batch add case button

      navForm.find('input.tag_add').on('click', function () {
        let selectedCaseIDs = getSelectedCaseIDs(casesTable);
        if (selectedCaseIDs.length === 0) {
          showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
          return false;
        }

        let dialog = Nitrate.TestPlans.Details.addTagDialog;
        if (! dialog) {
          dialog = jQ('#addTagDialog').dialog({
            autoOpen: false,
            resizable: false,
            modal: true,
            height: 200,
            close: function (event, ui) {
              jQ(this).find('input[type=text]').prop('value', '');
            },
            open: function (event, ui) {
              jQ(this).find('input[type=text]').focus();
            },
            buttons: {
              Add: function () {
                dialog.find('#addTagForm').trigger('submit');
                dialog.dialog('close');
              },
              Cancel: function () {
                dialog.dialog('close');
              }
            }
          });
          Nitrate.TestPlans.Details.addTagDialog = dialog;

          dialog.find('#add_tag_plan').autocomplete({
            'minLength': 2,
            'appendTo': '#id_batch_add_tags_autocomplete',
            'source': function (request, response) {
              sendHTMLRequest({
                url: '/management/getinfo/',
                data: {
                  'name__startswith': request.term,
                  'info_type': 'tags',
                  'format': 'ulli',
                  'cases__plan__pk': planId,
                  'field': 'name'
                },
                success: function (data) {
                  let processedData = [];
                  if (data.indexOf('<li>') > -1) {
                    processedData = data
                      .slice(data.indexOf('<li>') + 4, data.lastIndexOf('</li>'))
                      .split('<li>')
                      .join('')
                      .split('</li>');
                  }
                  response(processedData);
                }
              });
            },
          });

          // Observe the batch tag form submit
          dialog.find('#addTagForm').on('submit', function (e) {
            e.stopPropagation();
            e.preventDefault();

            let tagData = Nitrate.Utils.formSerialize(this);
            if (! tagData.tags) {
              return false;
            }

            let params = Object.assign(
              serializeFormData({
                'form': navForm[0],
                'selectedCaseIDs': selectedCaseIDs,
                'hashable': true
              }),
              {
                tags: tagData.tags, a: 'add', t: 'json', f: 'serialized'
              }
            );

            /*
            * Two reasons to force to remove plan from parameters here.
            * 1. plan is added in previous cases filter. As the design
            *    of Show More, previous filter criteria is added for
            *    selecting all cases with same filter criteria.
            * 2. existing plan confuses tag view method due to it
            *    applies to both plan and case to add tag. Thus, the
            *    existing plan will cause it to add tag to all cases of
            *    that plan always.
            *
            * Placing this line of code is not a good idea. But, it
            * works well for the current implementation. Possible
            * solution to avoid this might to split the tag view method
            * to add tags to plans and cases, respectively. Why to make
            * change to tag view method? That is, according to the
            * cases filter implementation, plan must exist in the
            * filter criteria as a parameter.
            */
            delete params.plan;

            sendHTMLRequest({
              url: '/management/tags/',
              data: params,
              traditional: true,
              success: function (data, textStatus, xhr) {
                clearDialog(getDialog());
                reloadCases();
              },
            });
          });
        }

        dialog.dialog('open');
      });

      navForm.find('input.btn_component').on('click', function () {
        let selectedCaseIDs = getSelectedCaseIDs(casesTable);
        if (selectedCaseIDs.length === 0) {
          showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
          return;
        }

        let params = {
          'product': Nitrate.TestPlans.Instance.fields.product_id
        };

        let c = getDialog();
        renderComponentForm(c, params, function (e) {
          e.stopPropagation();
          e.preventDefault();

          let data = Nitrate.Utils.formSerialize(this);
          clearDialog(c);

          if (data.o_component === undefined || data.o_component.length === 0) {
            return true;
          }

          data.case = selectedCaseIDs;
          postRequestAndReloadCases('/cases/add-component/', data);
        });
      });

      navForm.find('input.btn_category').on('click', function () {
        let selectedCaseIDs = getSelectedCaseIDs(casesTable);
        if (selectedCaseIDs.length === 0) {
          showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
          return true;
        }

        let params = {
          'product': Nitrate.TestPlans.Instance.fields.product_id
        };

        let c = getDialog();
        renderCategoryForm(c, params, function (e) {
          e.stopPropagation();
          e.preventDefault();

          let data = Nitrate.Utils.formSerialize(this);
          clearDialog(c);

          if (data.o_category === undefined || data.o_category.length === 0) {
            return true;
          }

          data.case = selectedCaseIDs;
          postRequestAndReloadCases('/cases/category/', data);
        });
      });

      // Observe the batch remove tag function
      navForm.find('input.tag_delete').on('click', function () {
        let selectedCaseIDs = getSelectedCaseIDs(casesTable);
        if (selectedCaseIDs.length === 0) {
          showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
          return false;
        }

        let c = getDialog();

        renderTagForm(c, {case: selectedCaseIDs}, function (e) {
          e.stopPropagation();
          e.preventDefault();

          let data = Nitrate.Utils.formSerialize(this);
          clearDialog(c);

          if (data.o_tag === undefined || data.o_tag.length === 0) {
            return true;
          }

          data.case = selectedCaseIDs;
          postRequestAndReloadCases('/cases/tag/', data);
        });
      });

      bindEventsOnLoadedCases({
        cases_container: container,
        plan_id: planId,
        parameters: postData
      })(casesTable, navForm[0]);
    },
  });
}

function constructPlanComponentsZone(container, parameters, callback) {
  container =
    typeof container === 'string' ? jQ('#' + container) : container;

  let url = Nitrate.http.URLConf.reverse({name: 'plan_components'});

  sendHTMLRequest({
    url: url,
    data: parameters || {plan: Nitrate.TestPlans.Instance.pk},
    traditional: true,
    container: container,
    callbackAfterFillIn: function () {
      if (callback) {
        callback();
      }

      jQ('#id_form_plan_components').on('submit', function (e) {
        e.stopPropagation();
        e.preventDefault();
        let p = Nitrate.Utils.formSerialize(this);
        let submitButton = jQ(this).find(':submit')[0];
        p[submitButton.name] = submitButton.value;
        constructPlanComponentsZone(container, p, callback);
      });

      jQ('.link_remove_plan_component').on('click', function () {
        let c = confirm(defaultMessages.confirm.remove_case_component);
        if(!c) {
          return false;
        }
        let links = jQ('.link_remove_plan_component');
        let index = links.index(this);
        let component = jQ('input[type="checkbox"][name="component"]')[index];

        let p = Nitrate.Utils.formSerialize(jQ('#id_form_plan_components')[0]);
        p.component = component.value;
        p.a = 'remove';
        constructPlanComponentsZone(container, p, callback);
      });

      jQ('#components_table tbody tr td:nth-child(1)').shiftcheckbox({
        checkboxSelector: ':checkbox',
        selectAll: '#components_table .js-select-all',
      });

      jQ('.js-update-components').click(function () {
        constructPlanComponentModificationDialog();
      });

      jQ('#component_count').text(
        jQ('tbody#component').prop('count')
      );
    },
  });
}

function constructPlanComponentModificationDialog(container) {
  container = container || getDialog();
  jQ(container).show();

  let planId = Nitrate.TestPlans.Instance.pk;
  let d = jQ('<div>');

  // Get the form and insert into the dialog.
  constructPlanComponentsZone(d[0], {a: 'get_form', plan: planId}, function () {
    jQ(container).html(
      constructForm(
        d.html(),
        Nitrate.http.URLConf.reverse({name: 'plan_components'}),
        function (e) {
          e.stopPropagation();
          e.preventDefault();
          let submitButton = jQ(this).find(':submit')[0];
          constructPlanComponentsZone(
            'components',
            jQ(this).serialize() + '&' + submitButton.name + '=' + submitButton.value
          );
          clearDialog();
        },
        'Press "Ctrl" to select multiple default component',
        jQ('<input>', {'type': 'submit', 'name': 'a', 'value': 'Update'})[0]
      )
    );
  });
}

function renderTagForm(container, parameters, formObserve) {
  let d = jQ('<div>');
  if (!container) {
    container = getDialog();
  }
  jQ(container).show();

  postHTMLRequest({
    url: '/cases/tag/',
    data: parameters,
    traditional: true,
    container: d,
    callbackAfterFillIn: function () {
      let h = jQ('<input>', {'type': 'hidden', 'name': 'a', 'value': 'remove'});
      let a = jQ('<input>', {'type': 'submit', 'value': 'Remove'});
      let c = jQ('<label>');
      c.append(h);
      c.append(a);
      a.on('click', function () { h.val('remove'); });
      jQ(container).html(
        constructForm(
          d.html(), Nitrate.http.URLConf.reverse({name: 'cases_tag'}), formObserve,
          'Press "Ctrl" to select multiple default component', c[0]
        )
      );
    }
  });
}

function renderCategoryForm(container, parameters, formObserve) {
  let d = jQ('<div>');
  if (!container) {
    container = getDialog();
  }
  jQ(container).show();

  postHTMLRequest({
    url: '/cases/category/',
    data: parameters,
    container: d,
    callbackAfterFillIn: function () {
      let h = jQ('<input>', {'type': 'hidden', 'name': 'a', 'value': 'add'});
      let a = jQ('<input>', {'type': 'submit', 'value': 'Select'});
      let c = jQ('<label>');
      c.append(h);
      c.append(a);
      a.on('click', function () { h.val('update'); });
      jQ(container).html(
        constructForm(
          d.html(), '/cases/category/', formObserve, 'Select Category', c[0]
        )
      );
      registerProductAssociatedObjectUpdaters(
        document.getElementById('id_product'),
        false,
        [
          {
            func: getCategoriesByProductId,
            targetElement: document.getElementById('id_o_category'),
            addBlankOption: false
          }
        ]
      );
    }
  });
}

function sortCase(container, planId, order) {
  let form = jQ(container).children()[0];
  let parameters = Nitrate.Utils.formSerialize(form);
  parameters.a = 'sort';

  if (parameters.case_sort_by === order) {
    parameters.case_sort_by = '-' + order;
  } else {
    parameters.case_sort_by = order;
  }
  constructPlanDetailsCasesZone(container, planId, parameters);
}

function resortCasesDragAndDrop(container, button, form, table, parameters, callback) {
  if (button.innerHTML !== 'Done Sorting') {
    // Remove the elements affect the page
    jQ(form).parent().find('.blind_all_link').remove(); // Remove blind all link
    jQ(form).parent().find('.case_content').remove();
    jQ(form).parent().find('.blind_icon').remove();
    jQ(form).parent().find('.show_change_status_link').remove();
    jQ(table).parent().find('.expandable').unbind();

    // Use the selector content to replace the selector
    jQ(form).parent().find('.change_status_selector').each(function () {
      let w = this.selectedIndex;
      jQ(this).replaceWith((jQ('<span>')).html(this.options[w].text));
    });

    button.innerHTML = 'Done Sorting';
    jQ(table).parent().find('tr').addClass('cursor_move');

    jQ(table).tableDnD();
  } else {
    jQ(button).replaceWith((jQ('<span>')).html('...Submitting changes'));

    jQ(table).parent().find('input[type=checkbox]').each(function () {
      this.checked = true;
      this.disabled = false;
    });

    postRequest({
      url: 'reorder-cases/',
      data: parameters,
      traditional: true,
      success: callback,
    });
  }
}

function FocusTabOnPlanPage(element) {
  let tabName = element.hash.slice(1);
  jQ('#tab_treeview').removeClass('tab_focus');
  jQ('#treeview').hide();
  jQ('#tab_' + tabName).addClass('tab_focus').children('a').click();
  jQ('#' + tabName).show();
}

/*
 * Handle events within Runs tab in a plan page.
 */
Nitrate.TestPlans.Runs = {
  'bind': function () {
    // Bind everything.
    let that = this;
    jQ('#show_more_runs').on('click', that.showMore);
    jQ('#reload_runs').on('click', that.reload);
    jQ('#tab_testruns').on('click', that.initializeRunTab);
    jQ('.run_selector').on('change', that.reactsToRunSelection);
    jQ('#id_check_all_runs').on('change', that.reactsToAllRunSelectorChange);
  },
  'makeUrlFromPlanId': function (planId) {
    return '/plan/' + planId + '/runs/';
  },
  'render': function (data) {
    let tbody = jQ('#testruns_body');
    let html = jQ(data.html);
    let btnCheckAll = jQ('#box_select_rest input:checkbox');
    if (btnCheckAll.length > 0 && btnCheckAll.is(':checked')) {
      html.find('.run_selector').prop('checked', true);
    }
    tbody.append(html);
  },
  'initializeRunTab': function () {
    /*
     * Load the first page of the runs when:
     * 1. Current active tab is #testrun;
     * AND
     * 2. No testruns are ever loaded.
     *
     */
    let that = Nitrate.TestPlans.Runs;
    if (jQ('#tab_testruns').hasClass('tab_focus')) {
      if (!jQ.fn.DataTable.fnIsDataTable(jQ('#testruns_table')[0])) {
        let url = that.makeUrlFromPlanId(document.getElementById('testruns_table').dataset.planId);
        jQ('#testruns_table').dataTable(
          Object.assign({}, Nitrate.DataTable.commonSettings, {
            sAjaxSource: url,

            'aoColumnDefs':[
              {'bSortable': false, 'aTargets':[0, 8, 9, 10]},
              {'sType': 'numeric', 'aTargets': [1, 6, 8, 9, 10 ]},
              {'sType': 'date', 'aTargets': [5]}
            ],

            oLanguage: {
              sEmptyTable: 'No test run was found in this plan.'
            },

            fnServerParams: function (aoData) {
              let params = jQ('#run_filter').serializeArray();
              params.forEach(function (param) {
                aoData.push(param);
              });
            },

            fnDrawCallback: function () {
              jQ('#testruns_table tbody tr').shiftcheckbox({
                checkboxSelector: ':checkbox',
                selectAll: '#testruns_table .js-select-all'
              });
            }
          })
        );
      }
    }
  },
  'reactsToRunSelection': function () {
    let selection = jQ('.run_selector:not(:checked)');
    let controller = jQ('#id_check_all_runs');
    if (selection.length === 0) {
      controller.prop('checked', true);
    } else {
      controller.prop('checked', false);
    }
    controller.trigger('change');
  },
  'reactsToAllRunSelectorChange': function (event) {
    let that = Nitrate.TestPlans.Runs;
    if (jQ(event.target).prop('checked')) {
      that.toggleRemainingRunSelection('on');
    } else {
      that.toggleRemainingRunSelection('off');
    }
  },
  'toggleRemainingRunSelection': function (status) {
    let area = jQ('#box_select_rest');
    if (area.length) {
      if (status === 'off') {
        area.find('input:checkbox').prop('checked', false);
        area.hide();
      } else {
        area.find('input:checkbox').prop('checked', true);
        area.show();
      }
    }
  },
  'filter': function () {
    let queryString = jQ('#run_filter').serialize();
    // store this string into the rest result select box
    let box = jQ('#box_select_rest');
    box.find('input:checkbox').val(queryString);
    return queryString;
  },
  'reload': function () {
    jQ('#testruns_body').children().remove();
    jQ('#js-page-num').val('1');
    jQ('#testruns_table').dataTable().fnDraw();

    return false;
  }
};
