Nitrate.TestPlans = {};
Nitrate.TestPlans.Create = {};
Nitrate.TestPlans.List = {};
Nitrate.TestPlans.Advance_Search_List = {};
Nitrate.TestPlans.Details = {};
Nitrate.TestPlans.Edit = {};
Nitrate.TestPlans.SearchCase = {};
Nitrate.TestPlans.Clone = {};
Nitrate.TestPlans.Attachment = {};

/*
 * Hold container IDs
 */
Nitrate.TestPlans.CasesContainer = {
  // containing cases with confirmed status
  ConfirmedCases: 'testcases',
  // containing cases with non-confirmed status
  ReviewingCases: 'reviewcases'
};

/* eslint no-redeclare:off */
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

/**
 * Collect selected case IDs from a given container and submit them to a specific location. The
 * container element should have children HTMLInputElement with type checkbox and name case.
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
  'pk': Number(),
  'data': {},
  'tree_elements': jQ('<div>')[0],
  'default_container': 'id_tree_container',
  'default_parameters': {t: 'ajax'}, // FIXME: Doesn't make effect here.

  /**
   * A wrapper of jQ.ajax to filter specific plans.
   * @param {object} data - data to send to server side.
   * @param {function} callback - a function called when AJAX request succeeds and the parsed
   *                              response data will be passed in.
   */
  'filter': function (data, callback) {
    let requestData = Object.assign({}, data, {t: 'ajax'});
    let url = Nitrate.http.URLConf.reverse({name: 'plans'});
    getRequest({url: url, data: requestData, sync: true, success: callback});
  },

  'init': function (planId) {
    this.pk = planId;

    // Current, Parent, Brothers, Children, Temporary current
    let curPlan, parentPlan, brotherPlans, childPlans, tempCurPlan;

    // Get the current plan
    this.filter({pk: planId}, function (responseData) {
      if (responseData.length) {
        curPlan = responseData[0];
      }
    });
    if (!curPlan) {
      showModal('Plan ' + planId + ' can not found in database');
      return false;
    }

    // Get the parent plan
    if (curPlan.parent_id) {
      this.filter({pk: curPlan.parent_id}, function (responseData) {
        parentPlan = responseData[0];
      });
    }

    // Get the brother plans
    if (curPlan.parent_id) {
      this.filter({parent__pk: curPlan.parent_id}, function (responseData) {
        brotherPlans = responseData;
      });
    }

    // Get the child plans
    this.filter({parent__pk: curPlan.pk}, function (responseData) {
      childPlans = responseData;
    });

    // Combine all of plans
    // Presume the plan have parent and brother at first
    if (parentPlan && brotherPlans) {
      parentPlan.children = brotherPlans;
      tempCurPlan = this.traverse(parentPlan.children, curPlan.pk);
      tempCurPlan.is_current = true;
      if (childPlans) {
        tempCurPlan.children = childPlans;
      }

      if (parentPlan.pk) {
        parentPlan = Nitrate.Utils.convert('obj_to_list', parentPlan);
      }

      this.data = parentPlan;
    } else {
      curPlan.is_current = true;
      if (childPlans) {
        curPlan.children = childPlans;
      }
      this.data = Nitrate.Utils.convert('obj_to_list', curPlan);
    }
  },

  /**
   * An event handler will be hooked to "Up" button when render the tree.
   * @param {Event} e - HTML DOM event.
   */
  'up': function () {
    let tree = Nitrate.TestPlans.TreeView;
    let parentObj = null, brotherObj = null;

    tree.filter({pk: tree.data[0].parent_id}, function (responseData) {
      parentObj = {0: responseData[0], length: 1};
    });

    tree.filter({parent__pk: tree.data[0].parent_id}, function (responseData) {
      brotherObj = responseData;
    });

    if (parentObj && brotherObj.length) {
      parentObj[0].children = brotherObj;
      let brotherCount = brotherObj.length;
      for (let i = 0; i < brotherCount; i++) {
        if (parseInt(parentObj[0].children[i].pk) === parseInt(tree.data[0].pk)) {
          parentObj[0].children[i] = tree.data[0];
          break;
        }
      }
      tree.data = parentObj;
      tree.render_page();
    }
  },

  /**
   * Event handler hooked into the toggle icon click event.
   * @param {Event} e - the DOM event object.
   */
  'blind': function () {
    let tree = Nitrate.TestPlans.TreeView;
    let eContainer = this;
    let liContainer = jQ(eContainer).parent().parent();
    let ePk = jQ(eContainer).next('a').eq(0).html();
    let containerClns = jQ(eContainer).prop('class').split(/\s+/);
    let expandIconUrl = '/static/images/t2.gif';
    let collapseIconUrl = '/static/images/t1.gif';
    let obj = tree.traverse(tree.data, ePk);

    containerClns.forEach(function (className) {
      if (typeof className === 'string') {
        switch (className) {
          case 'expand_icon':
            liContainer.find('ul').eq(0).hide();
            eContainer.src = collapseIconUrl;
            jQ(eContainer).removeClass('expand_icon').addClass('collapse_icon');
            break;

          case 'collapse_icon':
            if (typeof obj.children !== 'object' || obj.children === []) {
              tree.filter({parent__pk: ePk}, function (responseData) {
                let data = Nitrate.Utils.convert('obj_to_list', responseData);
                tree.insert(obj, data);
                liContainer.append(tree.render(data));
              });
            }

            liContainer.find('ul').eq(0).show();
            eContainer.src = expandIconUrl;
            jQ(eContainer).removeClass('collapse_icon').addClass('expand_icon');
            break;
        }
      }
    });
  },

  'render': function (data) {
    let ul = jQ('<ul>');
    let iconExpand = '<img alt="expand" src="/static/images/t2.gif" class="expand_icon js-toggle-icon">';
    let iconCollapse = '<img alt="collapse" src="/static/images/t1.gif" class="collapse_icon js-toggle-icon">';

    // Add the 'Up' button
    if (!data && this.data) {
      data = this.data;
      if (data && data[0].parent_id) {
        let btn = jQ('<input>', {'type': 'button', 'value': 'Up'});
        btn.on('click', this.up);
        ul.append(jQ('<li>').html(btn).addClass('no-list-style'));
      }
    }

    // Add the child plans to parent
    for (let i in data) {
      let obj = data[i];
      if (!obj.pk) { continue; }

      let li = jQ('<li>');
      let title = ['[<a href="' + obj.get_url_path + '">' + obj.pk + '</a>] '];

      if (obj.num_children) {
        li.addClass('no-list-style');
        title.unshift(obj.children ? iconExpand : iconCollapse);
      }

      title.unshift(obj.is_active ? '<div>' : '<div class="line-through">');
      // Construct the items
      title.push('<a class="plan_name" href="' + obj.get_url_path + '">' + obj.name + '</a>');
      title.push(' (');

      let s = null;

      if (obj.num_cases) {
        s = obj.is_current ?
          '<a href="#testcases" onclick="FocusTabOnPlanPage(this)">' + obj.num_cases + ' cases</a>, ' :
          '<a href="' + obj.get_url_path + '#testcases">' + obj.num_cases + ' cases</a>, ';
      } else {
        s = '0 case, ';
      }
      title.push(s);

      if (obj.num_runs) {
        s = obj.is_current ?
          '<a href="#testruns" onclick="FocusTabOnPlanPage(this)">' + obj.num_runs + ' runs</a>, ' :
          '<a href="' + obj.get_url_path + '#testruns">' + obj.num_runs + ' runs</a>, ';
      } else {
        s = '0 runs, ';
      }
      title.push(s);

      if (obj.num_children === 0) {
        s = '0 child';
      } else if (obj.num_children === 1) {
        s = obj.is_current ?
          '<a href="#treeview" onclick="expandCurrentPlan(jQ(this).parent()[0])">' + '1 child</a>' :
          '<a href="' + obj.get_url_path + '#treeview">' + '1 child</a>';
      } else {
        let numChildren = obj.num_children;
        s = obj.is_current ?
          '<a href="#treeview" onclick="expandCurrentPlan(jQ(this).parent()[0])">' + numChildren + ' children</a>' :
          '<a href="' + obj.get_url_path + '#treeview">' + numChildren + ' children</a>';
      }

      title.push(s);
      title.push(')</div>');

      ul.append(li.html(title.join('')));

      if (obj.is_current) {
        li.addClass('current');
      }
      if (obj.children) {
        li.append(this.render(obj.children));
      }
      li.find('.js-toggle-icon').on('click', this.blind);
    }

    return ul[0];
  },

  'render_page': function (container) {
    let _container = container || this.default_container;
    jQ('#' + _container).html(constructAjaxLoading());
    jQ('#' + _container).html(this.render());
  },

  'traverse': function (data, pk) {
    // http://stackoverflow.com/questions/3645678/javascript-get-a-reference-from-json-object-with-traverse
    for (let i in data) {
      let obj = data[i];
      if (obj === [] || typeof obj !== 'object') { continue; }
      if (typeof obj.pk === 'number' && parseInt(obj.pk) === parseInt(pk)) {
        return obj;
      }

      if (typeof obj.children === 'object') {
        let retVal = this.traverse(obj.children, pk);
        if (retVal !== undefined) { return retVal; }
      }
    }
  },

  'insert': function (node, data) {
    if (node.children) {
      return node;
    }

    node.children = data;
    return node;
  },

  'toggleRemoveChildPlanButton': function () {
    let treeContainer = jQ('#' + Nitrate.TestPlans.TreeView.default_container);
    let tvTabContainer = Nitrate.TestPlans.Details.getTabContentContainer({
      containerId: Nitrate.TestPlans.Details.tabContentContainerIds.treeview
    });
    let toEnableRemoveButton = treeContainer.find('.current').find('ul li').length > 0;
    tvTabContainer.find('.remove_node')[0].disabled = ! toEnableRemoveButton;
  },

  'addChildPlan': function (container, currentPlanId) {
    let self = this;
    let tree = Nitrate.TestPlans.TreeView;
    let childPlanIds = window.prompt('Enter a comma separated list of plan IDs').trim();
    if (!childPlanIds) {
      return false;
    }

    let cleanedChildPlanIds = [];
    let inputChildPlanIds = childPlanIds.split(',');

    for (let i = 0; i < inputChildPlanIds.length; i++) {
      let s = inputChildPlanIds[i].trim();
      if (s === '') { continue; }
      if (!/^\d+$/.test(s)) {
        showModal(
          'Plan Id should be a numeric. ' + s + ' is not valid.', 'Add child plan'
        );
        return;
      }
      let childPlanId = parseInt(s);
      let isParentOrThisPlan = childPlanId === parseInt(tree.data[0].pk) || childPlanId === currentPlanId;
      if (isParentOrThisPlan) {
        showModal('Cannot add parent or self.', 'Add child plan');
        return;
      }
      cleanedChildPlanIds.push(childPlanId);
    }

    previewPlan({pk__in: cleanedChildPlanIds.join(',')}, '', function (e) {
      e.stopPropagation();
      e.preventDefault();

      let planId = Nitrate.Utils.formSerialize(this).plan_id;
      updateObject('testplans.testplan', planId, 'parent', currentPlanId, 'int', function () {
        clearDialog();
        Nitrate.TestPlans.Details.loadPlansTreeView(currentPlanId);
        self.toggleRemoveChildPlanButton();
      });
    },
    'This operation will overwrite existing data');
  },

  'removeChildPlan': function (container, currentPlanId) {
    let self = this;
    let tree = Nitrate.TestPlans.TreeView;
    let childrenPks = tree.traverse(tree.data, currentPlanId).children.map(function (child) {
      return child.pk;
    });
    childrenPks.sort();

    let inputChildPlanIds = window.prompt('Enter a comma separated list of plan IDs to be removed');
    if (!inputChildPlanIds) {
      return false;
    }
    let cleanedChildPlanIds = [];
    inputChildPlanIds = inputChildPlanIds.split(',');
    for (let j = 0; j < inputChildPlanIds.length; j++) {
      let s = inputChildPlanIds[j].trim();
      if (s === '') { continue; }
      if (!/^\d+$/.test(s)) {
        showModal(
          'Plan ID must be a number. ' + inputChildPlanIds[j] + ' is not valid.',
          'Remove child plan'
        )
        return;
      }
      if (s === currentPlanId.toString()) {
        showModal('Cannot remove current plan.', 'Remove child plan');
        return;
      }
      if (childrenPks.indexOf(parseInt(s)) === -1) {
        showModal('Plan ' + s + ' is not the child node of current plan', 'Remove child plan');
        return;
      }
      cleanedChildPlanIds.push(s);
    }

    previewPlan({pk__in: cleanedChildPlanIds.join(',')}, '', function (e) {
      e.stopPropagation();
      e.preventDefault();

      let planId = Nitrate.Utils.formSerialize(this).plan_id;
      updateObject('testplans.testplan', planId, 'parent', 0, 'None', function () {
        clearDialog();
        Nitrate.TestPlans.Details.loadPlansTreeView(currentPlanId);
        self.toggleRemoveChildPlanButton();
      });
    },
    'This operation will overwrite existing data');
  },

  'changeParentPlan': function (container, currentPlanId) {
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

    previewPlan({plan_id: p}, '', function (e) {
      e.stopPropagation();
      e.preventDefault();

      let planId = Nitrate.Utils.formSerialize(this).plan_id;
      updateObject('testplans.testplan', currentPlanId, 'parent', planId, 'int', function () {
        let tree = Nitrate.TestPlans.TreeView;
        tree.filter({plan_id: p}, function (responseData) {
          let plan = Nitrate.Utils.convert('obj_to_list', responseData);

          if (tree.data[0].pk === currentPlanId) {
            plan[0].children = jQ.extend({}, tree.data);
            tree.data = plan;
            tree.render_page();
          } else {
            plan[0].children = jQ.extend({}, tree.data[0].children);
            tree.data = plan;
            tree.render_page();
          }

          clearDialog();
        });
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
    window.location.href = jQ(this).data('param');
  });
};

Nitrate.TestPlans.Advance_Search_List.on_load = function () {
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

  if (jQ('#column_add').length) {
    jQ('#column_add').on('change', function () {
      switch(this.value) {
        case 'col_product':
          jQ('#col_product_head').show();
          jQ('.col_product_content').show();
          jQ('#col_product_option').hide();
          break;
        case('col_product_version'):
          jQ('#col_product_version_head').show();
          jQ('.col_product_version_content').show();
          jQ('#col_product_veresion_option').hide();
          break;
      }
    });
  }

  jQ('input[name="plan_id"]').on('click', function () {
    if (this.checked) {
      jQ(this).parent().parent().addClass('selection_row');
    } else {
      jQ(this).parent().parent().removeClass('selection_row');
    }
  });

  jQ('.js-new-plan').on('click', function () {
    window.location = jQ(this).data('param');
  });
  jQ('.js-clone-plan').on('click', function () {
    postToURL(jQ(this).data('param'), Nitrate.Utils.formSerialize(this.form), 'get');
  });
  jQ('#plan_advance_printable').on('click', function () {
    postToURL(jQ(this).data('param'), Nitrate.Utils.formSerialize(this.form), 'get');
  });
  jQ('.js-export-cases').on('click', function () {
    postToURL(jQ(this).data('param'), Nitrate.Utils.formSerialize(this.form), 'get');
  });
};

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

  if (jQ('#column_add').length) {
    jQ('#column_add').on('change', function () {
      switch(this.value) {
        case 'col_product':
          jQ('#col_product_head').show();
          jQ('.col_product_content').show();
          jQ('#col_product_option').hide();
          break;
        case('col_product_version'):
          jQ('#col_product_version_head').show();
          jQ('.col_product_version_content').show();
          jQ('#col_product_veresion_option').hide();
          break;
      }
    });
  }

  jQ('input[name="plan_id"]').on('click', function () {
    if (this.checked) {
      jQ(this).parent().parent().addClass('selection_row');
    } else {
      jQ(this).parent().parent().removeClass('selection_row');
    }
  });

  if (jQ('#id_check_all_plans').length) {
    jQ('#id_check_all_plans').on('click', function () {
      jQ('#plan_list_printable').prop('disabled', !this.checked);
    });
  }

  if (jQ('#testplans_table').length) {
    jQ('#testplans_table').dataTable({
      'iDisplayLength': 20,
      'sPaginationType': 'full_numbers',
      'bFilter': false,
      // 'bLengthChange': false,
      'aLengthMenu': [[10, 20, 50, -1], [10, 20, 50, 'All']],
      'aaSorting': [[ 1, 'desc' ]],
      'bProcessing': true,
      'bServerSide': true,
      'sAjaxSource': '/plans/ajax/' + this.window.location.search,
      'aoColumns': [
        {'bSortable': false},
        null,
        {'sType': 'html'},
        {'sType': 'html'},
        {'sType': 'html'},
        null,
        {'bVisible': false},
        null,
        {'bSortable': false},
        {'bSortable': false},
        {'bSortable': false}
      ],
      'fnDrawCallback': function () {
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
      }
    });
  }

  jQ('.js-new-plan').on('click', function () {
    window.location = jQ(this).data('param');
  });
  jQ('.js-clone-plan').on('click', function () {
    postToURL(jQ(this).data('param'), Nitrate.Utils.formSerialize(this.form), 'get');
  });
  jQ('#plan_list_printable').on('click', function () {
    postToURL(jQ(this).data('param'), Nitrate.Utils.formSerialize(this.form), 'get');
  });
  jQ('.js-export-cases').on('click', function () {
    postToURL(jQ(this).data('param'), Nitrate.Utils.formSerialize(this.form), 'get');
  });
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
  'getTabContentContainer': function (options) {
    let constants = Nitrate.TestPlans.Details.tabContentContainerIds;
    let id = constants[options.containerId];
    if (id === undefined) {
      return undefined;
    } else {
      return jQ('#' + id);
    }
  },
  /*
   * Lazy-loading TestPlans TreeView
   */
  'loadPlansTreeView': function (planId) {
    // Initial the tree view
    Nitrate.TestPlans.TreeView.init(planId);
    Nitrate.TestPlans.TreeView.render_page();
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
    jQ('a[href="' + switchTo + '"]').trigger('click');
  },
  /*
   * Load cases table.
   *
   * Proxy of global function with same name.
   */
  'loadCases': function (container, planId, parameters) {
    constructPlanDetailsCasesZone(container, planId, parameters);

    if (Nitrate.TestPlans.Details._bindEventsOnLoadedCases === undefined) {
      Nitrate.TestPlans.Details._bindEventsOnLoadedCases = bindEventsOnLoadedCases({
        'cases_container': container,
        'plan_id': planId,
        'parameters': parameters
      });
    }
  },
  // Loading newly created cases with proposal status to show table of these kind of cases.
  'loadConfirmedCases': function (planId) {
    let container = Nitrate.TestPlans.CasesContainer.ConfirmedCases;
    Nitrate.TestPlans.Details.loadCases(container, planId, {
      'a': 'initial',
      'template_type': 'case',
      'from_plan': planId
    });
  },
  // Loading reviewing cases to show table of these kind of cases.
  'loadReviewingCases': function (planId) {
    let container = Nitrate.TestPlans.CasesContainer.ReviewingCases;
    Nitrate.TestPlans.Details.loadCases(container, planId, {
      'a': 'initial',
      'template_type': 'review_case',
      'from_plan': planId
    });
  },
  'bindEventsOnLoadedCases': function (container) {
    let elem = typeof container === 'string' ? jQ('#' + container) : jQ(container);
    let form = elem.children()[0];
    let table = elem.children()[1];
    Nitrate.TestPlans.Details._bindEventsOnLoadedCases(table, form);
  },
  'observeEvents': function (planId) {
    let NTPD = Nitrate.TestPlans.Details;

    jQ('#tab_testcases').on('click', function () {
      if (!NTPD.testcasesTabOpened) {
        NTPD.loadConfirmedCases(planId);
        NTPD.testcasesTabOpened = true;
      }
    });

    jQ('#tab_treeview').on('click', function () {
      if (!NTPD.plansTreeViewOpened) {
        NTPD.loadPlansTreeView(planId);
        NTPD.plansTreeViewOpened = true;
      }
    });

    jQ('#tab_reviewcases').on('click', function () {
      if (!Nitrate.TestPlans.Details.reviewingCasesTabOpened) {
        Nitrate.TestPlans.Details.loadReviewingCases(planId);
        Nitrate.TestPlans.Details.reviewingCasesTabOpened = true;
      }
    });

    // Initial the enable/disble btns
    if (jQ('#btn_disable').length) {
      jQ('#btn_disable').on('click', function (){
        updateObject('testplans.testplan', planId, 'is_active', 'False', 'bool');
      });
    }

    if (jQ('#btn_enable').length) {
      jQ('#btn_enable').on('click', function () {
        updateObject('testplans.testplan', planId, 'is_active', 'True', 'bool');
      });
    }
  },
  'reopenCasesTabThen': function () {
    Nitrate.TestPlans.Details.testcasesTabOpened = false;
  },
  'reopenReviewingCasesTabThen': function () {
    Nitrate.TestPlans.Details.reviewingCasesTabOpened = false;
  },
  /*
   * Helper function to reopen other tabs.
   *
   * Arguments:
   * - container: a jQuery object, where the operation happens to reopen other tabs. The container
   *              Id is used to select the reopen operations.
   */
  'reopenTabHelper': function (container) {
    let switchMap = {
      'testcases': function () {
        Nitrate.TestPlans.Details.reopenReviewingCasesTabThen();
      },
      'reviewcases': function () {
        Nitrate.TestPlans.Details.reopenCasesTabThen();
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

    jQ('#btn_edit').on('click', function () {
      window.location.href = jQ(this).data('param');
    });
    jQ('#btn_clone, #btn_export, #btn_print').on('click', function () {
      let params = jQ(this).data('params');
      window.location.href = params[0] + '?plan=' + params[1];
    });
    jQ('#id_import_case_zone').find('.js-close-zone').on('click', function () {
      jQ('#id_import_case_zone').hide();
      jQ('#import-error').empty();
    });
    jQ('.js-del-attach').on('click', function () {
      let params = jQ(this).data('params');
      deleConfirm(params[0], 'from_plan', params[1]);
    });

    let treeview = jQ('#treeview')[0];
    let planPK = parseInt(jQ('#id_tree_container').data('param'));

    jQ('#js-change-parent-node').on('click', function () {
      Nitrate.TestPlans.TreeView.changeParentPlan(treeview, planPK);
    });
    jQ('#js-add-child-node').on('click', function () {
      Nitrate.TestPlans.TreeView.addChildPlan(treeview, planPK);
    });
    jQ('#js-remove-child-node').on('click', function () {
      Nitrate.TestPlans.TreeView.removeChildPlan(treeview, planPK);
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
    jQ('#id_table_cases').dataTable({
      'aoColumnDefs':[{'bSortable':false, 'aTargets':[ 'nosort' ]}],
      'aaSorting': [[ 1, 'desc' ]],
      'sPaginationType': 'full_numbers',
      'bFilter': false,
      'aLengthMenu': [[10, 20, 50, -1], [10, 20, 50, 'All']],
      'iDisplayLength': 20,
      'bProcessing': true,
      'fnDrawCallback': function () {
        jQ('#id_table_cases tbody tr td:nth-child(1)').shiftcheckbox({
          checkboxSelector: ':checkbox',
          selectAll: '#id_table_cases .js-select-all'
        });

        jQ('#id_table_cases :checkbox').on('change', function () {
          let disable = jQ('#id_table_cases tbody :checkbox:checked').length === 0;
          jQ('#add-selected-cases').prop('disabled', disable);
        });
      }
    });
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

    jQ('.js-del-attach').on('click', function () {
      let params = jQ(this).data('params');
      deleConfirm(params[0], params[1], params[2]);
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

/**
 * Unlink selected cases from current TestPlan.
 *
 * Rewrite function unlinkCasePlan to avoid conflict. Remove it when confirm it's not used any more.
 */
function unlinkCasesFromPlan(container, form, table) {
  let selectedCaseIDs = getSelectedCaseIDs(table);
  if (selectedCaseIDs.length === 0) {
    return;
  }
  if (! confirm('Are you sure you want to remove test case(s) from this test plan?')) {
    return false;
  }

  postRequest({
    url: 'delete-cases/',
    data: {case: selectedCaseIDs},
    traditional: true,
    success: function () {
      // Form data contains cases filter criteria set previously.
      // Those criteria will be used to reload cases.
      let formData = Nitrate.Utils.formSerialize(form);
      formData.a = 'initial';
      constructPlanDetailsCasesZone(container, formData.from_plan, formData);
      return true;
    },
  });
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

  updateObject('testcases.testcaseplan', parameters.testcaseplan, 'sortkey', 'nsk', 'int', callback);
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

    // Display/Hide the case content
    jQ(container).parent().find('.expandable.js-just-loaded').on('click', function () {
      let btn = this;
      let title = jQ(this).parent()[0]; // Container
      let content = jQ(this).parent().next()[0]; // Content Containers
      let caseId = title.id;
      let templateType = jQ(form).parent().find('input[name="template_type"]')[0].value;

      if (templateType === 'case') {
        toggleTestCasePane({
          'case_id': caseId,
          'casePaneContainer': jQ(content)
        });
        toggleExpandArrow({
          'caseRowContainer': jQ(title),
          'expandPaneContainer': jQ(content)
        });
        return;
      }

      // Review case content call back;
      let reviewCaseContentCallback = function () {
        let commentContainerT = jQ('<div>')[0];

        // Change status/comment callback
        jQ(content).parent().find('.update_form').unbind('submit').on('submit', function (e) {
          e.stopPropagation();
          e.preventDefault();

          let params = Nitrate.Utils.formSerialize(this);
          submitComment(commentContainerT, params, function () {
            let td = jQ('<td>', {colspan: 12});
            td.append(constructAjaxLoading('id_loading_' + params.object_pk));
            jQ(content).html(td);
            // FIXME: refresh the content only once
            jQ(btn).trigger('click');
            jQ(btn).trigger('click');
          });
        });

        // Observe the delete comment form
        jQ(content).parent().find('.form_comment').off('submit').on('submit', function (e) {
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
            jQ(content).html(td);
            // FIXME: refresh the content only once.
            jQ(btn).trigger('click');
            jQ(btn).trigger('click');
          });
        });
      };

      let caseContentCallback = null;
      switch(templateType) {
        case 'review_case':
          caseContentCallback = reviewCaseContentCallback;
          break;
        default:
          caseContentCallback = function () {};
      }

      toggleTestCasePane(
        {
          'case_id': caseId,
          'casePaneContainer': jQ(content),
          'reviewing': true
        },
        caseContentCallback
      );
      toggleExpandArrow({
        'caseRowContainer': jQ(title),
        'expandPaneContainer': jQ(content)
      });
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
 * @param {Object} options
 * @property {HTMLElement} options.zoneContainer
 * @property {string[]} options.selectedCaseIDs
 * @property {boolean} options.hashable
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


/*
 * Event handler invoked when TestCases' Status is changed.
 */
function onTestCaseStatusChange(options) {
  let container = options.container;

  return function () {
    let selectedCaseIDs = getSelectedCaseIDs(options.table);
    if (selectedCaseIDs.length === 0) {
      showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
      return false;
    }
    let statusPk = this.value;
    if (!statusPk) {
      return false;
    }

    confirmDialog({
      message: defaultMessages.confirm.change_case_status,
      title: 'Manage Test Case Status',
      yesFunc: function () {
        let postdata = serializeFormData({
          'form': options.form,
          'zoneContainer': container,
          'selectedCaseIDs': selectedCaseIDs,
          'hashable': true
        });
        postdata.a = 'update';

        postRequest({
          url: '/ajax/update/case-status/',
          data: {
            'from_plan': postdata.from_plan,
            'case': postdata.case,
            'target_field': 'case_status',
            'new_value': statusPk
          },
          traditional: true,
          success: function (data) {
            constructPlanDetailsCasesZone(container, options.planId, postdata);

            jQ('#run_case_count').text(data.run_case_count);
            jQ('#case_count').text(data.case_count);
            jQ('#review_case_count').text(data.review_case_count);

            Nitrate.TestPlans.Details.reopenTabHelper(jQ(container));
          },
        });
      }
    });
  };
}


/*
 * Event handler invoked when TestCases' Priority is changed.
 */
function onTestCasePriorityChange(options) {
  let container = options.container;

  return function () {
    let selectedCaseIDs = getSelectedCaseIDs(options.table);
    if (selectedCaseIDs.length === 0) {
      showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
      return false;
    }

    // FIXME: how about show a message to user to let user know what is happening?
    let newPriority = this.value;

    if (! newPriority) {
      return false;
    }

    confirmDialog({
      message: defaultMessages.confirm.change_case_priority,
      title: 'Manage Test Case Priority',
      yesFunc: function () {
        let postdata = serializeFormData({
          'form': options.form,
          'zoneContainer': container,
          'selectedCaseIDs': selectedCaseIDs,
          'hashable': true
        });
        postdata.a = 'update';

        postRequest({
          url: '/ajax/update/cases-priority/',
          data: {
            from_plan: postdata.from_plan,
            case: postdata.case,
            target_field: 'priority',
            new_value: newPriority
          },
          traditional: true,
          success: function () {
            constructPlanDetailsCasesZone(container, options.planId, postdata);
          },
        });
      }
    });
  };
}

function getForm(container, appForm, parameters, callback, format) {
  if (!parameters) {
    parameters = {};
  }

  parameters.app_form = appForm;
  parameters.format = format;

  sendHTMLRequest({
    url: Nitrate.http.URLConf.reverse({name: 'get_form'}),
    data: parameters,
    container: container,
    callbackAfterFillIn: callback
  });
}


function constructCaseAutomatedForm(container, options, callback) {
  jQ(container).html(constructAjaxLoading());
  jQ(container).show();
  let d = jQ('<div>', {'class': 'automated_form'})[0];

  getForm(d, 'testcases.CaseAutomatedForm', {}, function (jqXHR) {
    let returntext = jqXHR.responseText;

    jQ(container).html(
      constructForm(returntext, '/cases/automated/', function (e) {
        e.stopPropagation();
        e.preventDefault();

        if (!jQ(this).find('input[type="checkbox"]:checked').length) {
          showModal('Nothing selected', 'Make case automated');
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
        let url = Nitrate.http.URLConf.reverse({name: 'cases_automated'});
        postRequest({url: url, data: params, success: callback});
      })
    );
  });
}

/*
 * Event handler invoked when TestCases' Automated is changed.
 */
function onTestCaseAutomatedClick(options) {
  let container = options.container;

  return function () {
    let selectedCaseIDs = getSelectedCaseIDs(options.table);
    if (selectedCaseIDs.length === 0) {
      showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
      return false;
    }

    let dialogContainer = getDialog();

    constructCaseAutomatedForm(
      dialogContainer,
      {'zoneContainer': container, 'selectedCaseIDs': selectedCaseIDs},
      function () {
        let params = Nitrate.Utils.formSerialize(options.form);
        /*
         * FIXME: this is confuse. There is no need to assign this
         *        value explicitly when update component and category.
         */
        params.a = 'search';
        params.case = selectedCaseIDs;
        constructPlanDetailsCasesZone(container, options.planId, params);
        clearDialog(dialogContainer);
      });
  };
}

/*
 * To change selected cases' tag.
 */
function onTestCaseTagFormSubmitClick(options) {
  let container = options.container;

  return function (response) {
    let dialog = getDialog();
    clearDialog(dialog);

    let returnobj = jQ.parseJSON(response.responseText);

    let template = Handlebars.compile(jQ('#batch_tag_summary_template').html());
    jQ(dialog).html(template({'tags': returnobj}))
      .find('.js-close-button').on('click', function () {
        jQ(dialog).hide();
      })
      .end().show();

    let params = Nitrate.Utils.formSerialize(options.form);
    params.case = getSelectedCaseIDs(options.table);
    params.a = 'initial';
    constructPlanDetailsCasesZone(container, options.planId, params);
  };
}

function onTestCaseTagAddClick(options) {
  return function () {
    let selectedCaseIDs = getSelectedCaseIDs(options.table);
    if (selectedCaseIDs.length === 0) {
      showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
      return false;
    }

    constructBatchTagProcessDialog(options.planId);

    // Observe the batch tag form submit
    jQ('#id_batch_tag_form').on('submit', function (e) {
      e.stopPropagation();
      e.preventDefault();

      let tagData = Nitrate.Utils.formSerialize(this);
      if (!tagData.tags) {
        return false;
      }
      let params = Object.assign(
        serializeFormData({
          'form': options.form,
          'zoneContainer': options.container,
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

      /* @function */
      let callback = onTestCaseTagFormSubmitClick({
        'container': options.container,
        'form': options.form,
        'planId': options.planId,
        'table': options.table
      });

      sendHTMLRequest({
        url: '/management/tags/',
        data: params,
        traditional: true,
        success: function (data, textStatus, xhr) { callback(xhr); },
      });
    });
  };
}

function renderTagForm(container, parameters, formObserve) {
  let d = jQ('<div>');
  if (!container) {
    container = getDialog();
  }
  jQ(container).show();

  postHTMLRequest({
    url: Nitrate.http.URLConf.reverse({name: 'cases_tag'}),
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

function onTestCaseTagDeleteClick(options) {
  let parameters = options.parameters;

  return function () {
    let c = getDialog();
    let selectedCaseIDs = getSelectedCaseIDs(options.table);
    if (selectedCaseIDs.length === 0) {
      showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
      return false;
    }

    renderTagForm(c, {case: selectedCaseIDs}, function (e) {
      e.stopPropagation();
      e.preventDefault();

      let url = Nitrate.http.URLConf.reverse({name: 'cases_tag'});
      postRequest({
        url: url,
        data: serializeFormData({
          form: this,
          zoneContainer: options.container,
          selectedCaseIDs: selectedCaseIDs,
        }),
        success: function () {
          // TODO: test whether params is enough instead of referencing parameters.
          parameters['case'] = selectedCaseIDs;
          constructPlanDetailsCasesZone(options.container, options.planId, parameters);
          clearDialog(c);
        },
      });
    });
  };
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

/*
 * To change selected cases' sort number.
 */
function onTestCaseSortNumberClick(options) {
  return function () {
    // NOTE: new implementation does not use testcaseplan.pk
    let selectedCaseIDs = getSelectedCaseIDs(options.table);
    if (selectedCaseIDs.length === 0) {
      showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
      return false;
    }

    let postdata = serializeFormData({
      'form': options.form,
      'zoneContainer': options.container,
      'selectedCaseIDs': selectedCaseIDs,
      'hashable': true
    });

    changeCaseOrder2(postdata, function () {
      postdata.case = selectedCaseIDs;
      constructPlanDetailsCasesZone(options.container, options.planId, postdata);
    });
  };
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

/*
 * To change selected cases' category.
 */
function onTestCaseCategoryClick(options) {
  let container = options.container;
  let parameters = options.parameters;

  return function () {
    if (this.disabled) {
      return false;
    }
    let c = getDialog();
    let params = {
      /*
       * FIXME: the first time execute this code, it's unnecessary
       *        to pass selected cases' ids to the server.
       */
      'case': getSelectedCaseIDs(options.table),
      'product': Nitrate.TestPlans.Instance.fields.product_id
    };
    if (params['case'] && params['case'].length === 0) {
      showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
      return false;
    }

    renderCategoryForm(c, params, function (e) {
      e.stopPropagation();
      e.preventDefault();

      let selectedCaseIDs = getSelectedCaseIDs(options.table);
      if (selectedCaseIDs.length === 0) {
        showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
        return false;
      }

      let params = serializeFormData({
        'form': this,
        'zoneContainer': container,
        'selectedCaseIDs': selectedCaseIDs
      });
      if (params.indexOf('o_category') < 0) {
        showModal(defaultMessages.alert.no_category_selected, 'Missing something?');
        return false;
      }

      postRequest({url: '/cases/category/', data: params, success: function () {
        // TODO: whether can use params rather than parameters.
        parameters.case = selectedCaseIDs;
        constructPlanDetailsCasesZone(container, options.planId, parameters);
        clearDialog(c);
      }});
    });
  };
}

/*
 * To change selected cases' default tester.
 */
function onTestCaseDefaultTesterClick(options) {
  return function () {
    let selectedCaseIDs = getSelectedCaseIDs(options.table);
    if (selectedCaseIDs.length === 0) {
      showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
      return false;
    }

    let emailOrUsername = window.prompt('Please type new email or username');
    if (!emailOrUsername) {
      return false;
    }

    let params = serializeFormData({
      'form': options.form,
      'zoneContainer': options.container,
      'selectedCaseIDs': selectedCaseIDs,
      'hashable': true
    });
    params.a = 'update';

    postRequest({
      url: '/ajax/update/cases-default-tester/',
      data: {
        from_plan: params.from_plan,
        case: params.case,
        target_field: 'default_tester',
        new_value: emailOrUsername
      },
      traditional: true,
      success: function () {
        constructPlanDetailsCasesZone(options.container, options.planId, params);
      },
    });
  };
}


/*
 * To change selected cases' component.
 */
function onTestCaseComponentClick(options) {
  let container = options.container;
  let parameters = options.parameters;

  return function () {
    if (this.disabled) {
      return false;
    }
    let c = getDialog();
    let params = {
      // FIXME: remove this line. It's unnecessary any more.
      'case': getSelectedCaseIDs(options.table),
      'product': Nitrate.TestPlans.Instance.fields.product_id
    };
    if (params['case'] && params['case'].length === 0) {
      showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
      return false;
    }

    renderComponentForm(c, params, function (e) {
      e.stopPropagation();
      e.preventDefault();

      let selectedCaseIDs = getSelectedCaseIDs(options.table);
      if (selectedCaseIDs.length === 0) {
        showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
        return false;
      }

      postRequest({
        url: '/cases/add-component/',
        data: serializeFormData({
          form: this,
          zoneContainer: container,
          selectedCaseIDs: selectedCaseIDs
        }),
        traditional: true,
        success: function () {
          parameters.case = selectedCaseIDs;
          constructPlanDetailsCasesZone(container, options.planId, parameters);
          clearDialog(c);
        },
      });
    });
  };
}


/**
 * To change selected cases' reviewer.
 */
function onTestCaseReviewerClick(options) {
  let form = options.form;
  let parameters = options.parameters;

  return function () {
    let selectedCaseIDs = getSelectedCaseIDs(options.table);
    if (selectedCaseIDs.length === 0) {
      showModal(defaultMessages.alert.no_case_selected, 'Missing something?');
      return false;
    }

    let emailOrUsername = window.prompt('Please type new email or username');
    if (!emailOrUsername) {
      return false;
    }

    let postdata = serializeFormData({
      'form': form,
      'zoneContainer': options.container,
      'selectedCaseIDs': selectedCaseIDs,
      'hashable': true
    });
    postdata.a = 'update';

    postRequest({
      url: '/ajax/update/cases-reviewer/',
      data: {
        from_plan: postdata.plan,
        case: postdata.case,
        target_field: 'reviewer',
        new_value:emailOrUsername
      },
      traditional: true,
      success: function () {
        constructPlanDetailsCasesZone(options.container, options.planId, parameters);
      },
    });
  };
}

/*
 * Callback for constructPlanDetailsCasesZone.
 */
function constructPlanDetailsCasesZoneCallback(options) {
  let container = options.container;
  let planId = options.planId;
  let parameters = options.parameters;

  return function () {
    let form = jQ(container).children()[0];
    let table = jQ(container).children()[1];

    // Presume the first form element is the form
    if (form.tagName !== 'FORM') {
      showModal('form element of container is not a form', 'Programming Error');
      return false;
    }

    let filter = jQ(form).parent().find('.list_filter')[0];

    // Filter cases
    jQ(form).on('submit', function (e) {
      e.stopPropagation();
      e.preventDefault();
      constructPlanDetailsCasesZone(container, planId, Nitrate.Utils.formSerialize(form));
    });

    // Change the case backgroud after selected
    jQ(form).parent().find('input[name="case"]').on('click', function () {
      if (this.checked) {
        jQ(this).parent().parent().addClass('selection_row');
      } else {
        jQ(this).parent().parent().removeClass('selection_row');
      }
    });

    if (jQ(form).parent().find('.btn_filter').length) {
      let element = jQ(form).parent().find('.btn_filter')[0];
      jQ(element).on('click', function () {
        if (filter.style.display === 'none') {
          jQ(filter).show();
          jQ(this).html(defaultMessages.link.hide_filter);
        } else {
          jQ(filter).hide();
          jQ(this).html(defaultMessages.link.show_filter);
        }
      });
    }

    // Bind click the tags in tags list to tags field in filter
    if (jQ(form).parent().find('.taglist a[href="#testcases"]').length) {
      jQ(form).parent().find('.taglist a').on('click', function () {
        if (filter.style.display === 'none') {
          jQ(form).parent().find('.filtercase').trigger('click');
        }
        if (form.tag__name__in.value) {
          form.tag__name__in.value = form.tag__name__in.value + ',' + this.textContent;
        } else {
          form.tag__name__in.value = this.textContent;
        }
      });
    }

    // Bind the sort link
    if (jQ(form).parent().find('.btn_sort').length) {
      let element = jQ(form).parent().find('.btn_sort')[0];
      jQ(element).on('click', function () {
        let params = Nitrate.Utils.formSerialize(form);
        params.case = getSelectedCaseIDs(table);
        resortCasesDragAndDrop(container, this, form, table, params, function () {
          params.a = 'initial';
          constructPlanDetailsCasesZone(container, planId, params);
        });
      });
    }

    // Bind batch change case status selector
    let element = jQ(form).parent().find('input[name="new_case_status_id"]')[0];
    if (element !== undefined) {
      jQ(element).on('change', onTestCaseStatusChange({
        'form': form, 'table': table, 'container': container, 'planId': planId
      }));
    }

    element = jQ(form).parent().find('input[name="new_priority_id"]')[0];
    if (element !== undefined) {
      jQ(element).on('change', onTestCasePriorityChange({
        'form': form, 'table': table, 'container': container, 'planId': planId
      }));
    }

    // Observe the batch case automated status button
    element = jQ(form).parent().find('input.btn_automated')[0];
    if (element !== undefined) {
      jQ(element).on('click', onTestCaseAutomatedClick({
        'form': form, 'table': table, 'container': container, 'planId': planId
      }));
    }

    element = jQ(form).parent().find('input.btn_component')[0];
    if (element !== undefined) {
      jQ(element).on('click', onTestCaseComponentClick({
        'container': container, 'form': form, 'planId': planId, 'table': table, 'parameters': parameters
      }));
    }

    element = jQ(form).parent().find('input.btn_category')[0];
    if (element !== undefined) {
      jQ(element).on('click', onTestCaseCategoryClick({
        'container': container, 'form': form, 'planId': planId, 'table': table, 'parameters': parameters
      }));
    }

    element = jQ(form).parent().find('input.btn_default_tester')[0];
    if (element !== undefined) {
      jQ(element).on('click', onTestCaseDefaultTesterClick({
        'container': container, 'form': form, 'planId': planId, 'table': table
      }));
    }

    element = jQ(form).parent().find('input.sort_list')[0];
    if (element !== undefined) {
      jQ(element).on('click', onTestCaseSortNumberClick({
        'container': container, 'form': form, 'planId': planId, 'table': table
      }));
    }

    element = jQ(form).parent().find('input.btn_reviewer')[0];
    if (element !== undefined) {
      jQ(element).on('click', onTestCaseReviewerClick({
        'container': container, 'form': form, 'planId': planId, 'table': table, 'parameters': parameters
      }));
    }

    // Observe the batch add case button
    element = jQ(form).parent().find('input.tag_add')[0];
    if (element !== undefined) {
      jQ(element).on('click', onTestCaseTagAddClick({
        'container': container, 'form': form, 'planId': planId, 'table': table
      }));
    }

    // Observe the batch remove tag function
    element = jQ(form).parent().find('input.tag_delete')[0];
    if (element !== undefined) {
      jQ(element).on('click', onTestCaseTagDeleteClick({
        'container': container, 'form': form, 'planId': planId, 'table': table, 'parameters': parameters
      }));
    }

    bindEventsOnLoadedCases(
      {'cases_container': container, 'plan_id': planId, 'parameters': parameters}
    )(table, form);
  };
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
      element.title = 'Collapse all cases';
      blinddownAllCases(element);
    } else {
      element.title = 'Expand all cases';
      blindupAllCases(element);
    }
  }
}

function constructPlanDetailsCasesZone(container, planId, parameters) {
  container = typeof container === 'string' ? jQ('#' + container)[0] : container;
  jQ(container).html(constructAjaxLoading());
  let postData = parameters || {a: 'initial', from_plan: planId};
  postHTMLRequest({
    url: '/cases/',
    data: postData,
    traditional: true,
    container: container,
    callbackAfterFillIn: function () {
      jQ('.show_change_status_link').on('click', function () {
        jQ(this).hide().next().show();
      });

      let type = typeof parameters.template_type === 'string' ?
        (parameters.template_type === 'case') ? '-' : '-review-' :
        (parameters.template_type[0] === 'case') ? '-' : '-review-';
      let casesSection = (type === '-') ? jQ('#testcases')[0] : jQ('#reviewcases')[0];
      let casesTable = jQ(casesSection).find('.js-cases-list')[0];
      let navForm = jQ('#js' + type + 'cases-nav-form')[0];

      jQ(casesTable).find('tbody .selector_cell').shiftcheckbox({
        checkboxSelector: ':checkbox',
        selectAll: jQ(casesTable).find('.js-select-all')
      });

      jQ('#js' + type + 'case-menu, #js' + type + 'new-case').on('click', function () {
        let params = jQ(this).data('params');
        window.location.href = params[0] + '?from_plan=' + params[1];
      });
      jQ('#js' + type + 'import-case').on('click', function () {
        jQ('#id_import_case_zone').toggle();
      });
      jQ('#js' + type + 'add-case-to-plan').on('click', function () {
        window.location.href = jQ(this).data('param');
      });
      jQ('#js' + type + 'export-case').on('click', function () {
        submitSelectedCaseIDs(jQ(this).data('param'), casesTable);
      });
      jQ('#js' + type + 'print-case').on('click', function () {
        submitSelectedCaseIDs(jQ(this).data('param'), casesTable);
      });
      jQ('#js' + type + 'clone-case').on('click', function () {
        postToURL(jQ(this).data('param'), {
          from_plan: Nitrate.Utils.formSerialize(navForm).from_plan,
          case: getSelectedCaseIDs(casesTable)
        },
        'get');
      });
      jQ('#js' + type + 'remove-case').on('click', function () {
        unlinkCasesFromPlan(casesSection, navForm, casesTable);
      });
      jQ('#js' + type + 'new-run').on('click', function () {
        postToURL(jQ(this).data('param'), {
          from_plan: Nitrate.Utils.formSerialize(navForm).from_plan,
          case: getSelectedCaseIDs(casesTable)
        });
      });
      jQ('#js' + type + 'add-case-to-run').on('click', function () {
        postToURL(jQ(this).data('param'), {case: getSelectedCaseIDs(casesTable)}, 'get');
      });
      jQ('.js' + type + 'status-item').on('click', function () {
        this.form.new_case_status_id.value = jQ(this).data('param');
        jQ(this.form.new_case_status_id).trigger('change');
      });
      jQ('.js' + type + 'priority-item').on('click', function () {
        this.form.new_priority_id.value = jQ(this).data('param');
        jQ(this.form.new_priority_id).trigger('change');
      });
      let $toggleAllCasesButton = (type === '-') ? jQ('#id_blind_all_link') : jQ('#review_id_blind_all_link');
      $toggleAllCasesButton.find('.collapse-all').on('click', function () {
        toggleAllCases(this);
      });
      jQ(casesTable).find('.js' + type + 'case-field').on('click', function () {
        sortCase(casesSection, jQ(this).parents('thead').data('param'), jQ(this).data('param'));
      });

      /* @function */
      let func = constructPlanDetailsCasesZoneCallback({
        'container': container,
        'planId': planId,
        'parameters': postData
      });
      func();
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

function constructBatchTagProcessDialog(planId) {
  let template = Handlebars.compile(jQ('#batch_tag_form_template').html());
  jQ('#dialog').html(template())
    .find('.js-cancel-button').on('click', function () {
      jQ('#dialog').hide();
    })
    .end().show();
  // Bind the autocomplete for tags
  jQ('#add_tag_plan').autocomplete({
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

/* eslint no-unused-vars: "off" */
function expandCurrentPlan(element) {
  let tree = Nitrate.TestPlans.TreeView;

  if (jQ(element).find('.collapse_icon').length) {
    let eContainer = jQ(element).find('.collapse_icon');
    let liContainer = eContainer.parent().parent();
    let ePk = eContainer.next('a').html();
    let obj = tree.traverse(tree.data, ePk);

    if (typeof obj.children !== 'object' || obj.children === []) {
      tree.filter({parent__pk: ePk}, function (responseData) {
        let objs = Nitrate.Utils.convert('obj_to_list', responseData);
        tree.insert(obj, objs);
        liContainer.append(tree.render(objs));
      });
    }

    liContainer.find('ul').first().show();
    eContainer
      .prop('src', '/static/images/t2.gif')
      .removeClass('collapse_icon')
      .addClass('expand_icon');
  }
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
        let url = that.makeUrlFromPlanId(jQ('#testruns_table').data('param'));
        jQ('#testruns_table').dataTable({
          'aoColumnDefs':[
            {'bSortable': false, 'aTargets':[0, 8, 9, 10]},
            {'sType': 'numeric', 'aTargets': [1, 6, 8, 9, 10 ]},
            {'sType': 'date', 'aTargets': [5]}
          ],
          'bSort': true,
          'bProcessing': true,
          'bFilter': false,
          'bLengthChange': false,
          'oLanguage': {'sEmptyTable': 'No test run was found in this plan.'},
          'bServerSide': true,
          'sAjaxSource': url,
          'iDisplayLength': 20,
          'sPaginationType': 'full_numbers',
          'fnServerParams': function (aoData) {
            let params = jQ('#run_filter').serializeArray();
            params.forEach(function (param) {
              aoData.push(param);
            });
          },
          'fnDrawCallback': function () {
            jQ('#testruns_table tbody tr').shiftcheckbox({
              checkboxSelector: ':checkbox',
              selectAll: '#testruns_table .js-select-all'
            });
          }
        });
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
