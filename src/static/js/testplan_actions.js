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


Nitrate.TestPlans.TreeView = {
  'pk': Number(),
  'data': {},
  'tree_elements': jQ('<div>')[0],
  'default_container': 'id_tree_container',
  'default_parameters': { t: 'ajax' }, // FIXME: Doesn't make effect here.

  /**
   * A wrapper of jQ.ajax to filter specific plans.
   * @param {object} data - data to send to server side.
   * @param {function} callback - a function called when AJAX request succeeds and the parsed
   *                              response data will be passed in.
   */
  'filter': function(data, callback) {
    let requestData = Object.assign({}, data, {t: 'ajax'});
    let url = Nitrate.http.URLConf.reverse({name: 'plans'});
    getRequest({url: url, data: requestData, sync: true, success: callback});
  },

  'init': function(plan_id) {
    this.pk = plan_id;

    // Current, Parent, Brothers, Children, Temporary current
    let curPlan, parentPlan, brotherPlans, childPlans, tempCurPlan;

    // Get the current plan
    this.filter({pk: plan_id}, function (responseData) {
      if (responseData.length) {
        curPlan = responseData[0];
      }
    });
    if (!curPlan) {
      window.alert('Plan ' + plan_id + ' can not found in database');
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
      tempCurPlan= this.traverse(parentPlan.children, curPlan.pk);
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
  'up': function(e) {
    let tree = Nitrate.TestPlans.TreeView;
    let parent_obj = null, brother_obj = null;

    tree.filter({pk: tree.data[0].parent_id}, function (responseData) {
      parent_obj = {0: responseData[0], length: 1};
    });

    tree.filter({parent__pk: tree.data[0].parent_id}, function (responseData) {
      brother_obj = responseData;
    });

    if (parent_obj && brother_obj.length) {
      parent_obj[0].children = brother_obj;
      let brotherCount = brother_obj.length;
      for (let i = 0; i < brotherCount; i++) {
        if (parseInt(parent_obj[0].children[i].pk) === parseInt(tree.data[0].pk)) {
           parent_obj[0].children[i] = tree.data[0];
           break;
        }
      }
      tree.data = parent_obj;
      tree.render_page();
    }
  },

  /**
   * Event handler hooked into the toggle icon click event.
   * @param {Event} e - the DOM event object.
   */
  'blind': function(e) {
    let tree = Nitrate.TestPlans.TreeView;
    let e_container = this;
    let li_container = jQ(e_container).parent().parent();
    let e_pk = jQ(e_container).next('a').eq(0).html();
    let container_clns = jQ(e_container).attr('class').split(/\s+/);
    let expand_icon_url = '/static/images/t2.gif';
    let collapse_icon_url = '/static/images/t1.gif';
    let obj = tree.traverse(tree.data, e_pk);

    container_clns.forEach(function(className, index) {
      if (typeof className === 'string') {
        switch (className) {
          case 'expand_icon':
            li_container.find('ul').eq(0).hide();
            e_container.src = collapse_icon_url;
            jQ(e_container).removeClass('expand_icon').addClass('collapse_icon');
            break;

          case 'collapse_icon':
            if (typeof obj.children !== 'object' || obj.children === []) {
              tree.filter({parent__pk: e_pk}, function (responseData) {
                let data = Nitrate.Utils.convert('obj_to_list', responseData);
                tree.insert(obj, data);
                li_container.append(tree.render(data));
              });
            }

            li_container.find('ul').eq(0).show();
            e_container.src = expand_icon_url;
            jQ(e_container).removeClass('collapse_icon').addClass('expand_icon');
            break;
        }
      }
    });
  },

  'render': function(data) {
    let ul = jQ('<ul>');
    let icon_expand = '<img alt="expand" src="/static/images/t2.gif" class="expand_icon js-toggle-icon">';
    let icon_collapse = '<img alt="collapse" src="/static/images/t1.gif" class="collapse_icon js-toggle-icon">';

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
      if (!obj.pk) continue;

      let li = jQ('<li>');
      let title = ['[<a href="' + obj.get_url_path + '">' + obj.pk + '</a>] '];

      if (obj.num_children) {
        li.addClass('no-list-style');
        title.unshift(obj.children ? icon_expand : icon_collapse);
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
        s= '0 case, ';
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
        s = obj.is_current ?
            '<a href="#treeview" onclick="expandCurrentPlan(jQ(this).parent()[0])">' + obj.num_children + ' children</a>' :
            '<a href="' + obj.get_url_path + '#treeview">' + obj.num_children + ' children</a>';
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

  'render_page': function(container) {
    let _container = container || this.default_container;
    jQ('#' + _container).html(getAjaxLoading());
    jQ('#' + _container).html(this.render());
  },

  'traverse': function(data, pk) {
    // http://stackoverflow.com/questions/3645678/javascript-get-a-reference-from-json-object-with-traverse
    for (let i in data) {
      let obj = data[i];
      if (obj === [] || typeof obj !== 'object') continue;
      if (typeof obj.pk === 'number' && parseInt(obj.pk) === parseInt(pk)) return obj;

      if (typeof obj.children === 'object') {
        let retVal = this.traverse(obj.children, pk);
        if (retVal !== undefined) return retVal;
      }
    }
  },

  'insert': function(node, data) {
    if (node.children) {
      return node;
    }

    node.children = data;
    return node;
  },

  'toggleRemoveChildPlanButton': function() {
    let treeContainer = jQ('#' + Nitrate.TestPlans.TreeView.default_container);
    let tvTabContainer = Nitrate.TestPlans.Details.getTabContentContainer({
      containerId: Nitrate.TestPlans.Details.tabContentContainerIds.treeview
    });
    let toEnableRemoveButton = treeContainer.find('.current').find('ul li').length > 0;
    tvTabContainer.find('.remove_node')[0].disabled = ! toEnableRemoveButton;
  },

  'addChildPlan': function(container, plan_id) {
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
      if (s === '') continue;
      if (!/^\d+$/.test(s)) {
        window.alert('Plan Id should be a numeric. ' + s + ' is not valid.');
        return;
      }
      let childPlanId = parseInt(s);
      let isParentOrThisPlan = childPlanId === parseInt(tree.data[0].pk) || childPlanId === plan_id;
      if (isParentOrThisPlan) {
        window.alert('Cannot add parent or self.');
        return;
      }
      cleanedChildPlanIds.push(childPlanId);
    }

    previewPlan({pk__in: cleanedChildPlanIds.join(',')}, '', function (e) {
      e.stopPropagation();
      e.preventDefault();

      let planId = Nitrate.Utils.formSerialize(this).plan_id;
      updateObject('testplans.testplan', planId, 'parent', plan_id, 'int', function () {
        clearDialog();
        Nitrate.TestPlans.Details.loadPlansTreeView(plan_id);
        self.toggleRemoveChildPlanButton();
      });
    },
    'This operation will overwrite existing data');
  },

  'removeChildPlan': function(container, plan_id) {
    let self = this;
    let tree = Nitrate.TestPlans.TreeView;
    let children_pks = tree.traverse(tree.data, plan_id).children.map(function (child) {
      return child.pk;
    });
    children_pks.sort();

    let inputChildPlanIds = window.prompt('Enter a comma separated list of plan IDs to be removed');
    if (!inputChildPlanIds) {
      return false;
    }
    let cleanedChildPlanIds = [];
    inputChildPlanIds = inputChildPlanIds.split(',');
    for (let j = 0; j < inputChildPlanIds.length; j++) {
      let s = inputChildPlanIds[j].trim();
      if (s === '') continue;
      if (!/^\d+$/.test(s)) {
        alert('Plan ID must be a number. ' + inputChildPlanIds[j] + ' is not valid.')
        return;
      }
      if (s === plan_id.toString()) {
        alert('Cannot remove current plan.');
        return;
      }
      if (children_pks.indexOf(parseInt(s)) === -1) {
        alert('Plan ' + s + ' is not the child node of current plan');
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
        Nitrate.TestPlans.Details.loadPlansTreeView(plan_id);
        self.toggleRemoveChildPlanButton();
      });
    },
    'This operation will overwrite existing data');
  },

  'changeParentPlan': function(container, plan_id) {
    let p = prompt('Enter new parent plan ID');
    if (!p) {
      return false;
    }
    let planId = window.parseInt(p);
    if (isNaN(planId)) {
      window.alert('Plan Id should be a numeric. ' + p + ' is invalid.');
      return false;
    }
    if (planId === plan_id) {
      window.alert('Parent plan should not be the current plan itself.');
      return false;
    }

    previewPlan({plan_id: p}, '', function (e) {
      e.stopPropagation();
      e.preventDefault();

      let planId = Nitrate.Utils.formSerialize(this).plan_id;
      updateObject('testplans.testplan', plan_id, 'parent', planId, 'int', function () {
        let tree = Nitrate.TestPlans.TreeView;
        tree.filter({plan_id: p}, function (responseData) {
          let plan = Nitrate.Utils.convert('obj_to_list', responseData);

          if (tree.data[0].pk === plan_id) {
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

Nitrate.TestPlans.Create.on_load = function() {
  bind_version_selector_to_product(true);

  jQ('#env_group_help_link').on('click', function(t) {
    jQ('#env_group_help').toggle();
  });
  jQ('#env_group_help_close').on('click', function(t) {
    jQ('#env_group_help').hide();
  });
  jQ('#add_id_product').on('click', function() {
    return popupAddAnotherWindow(this);
  });
  jQ('#add_id_product_version').on('click', function() {
    return popupAddAnotherWindow(this, 'product');
  });
  jQ('.js-cancel-button').on('click', function() {
    window.history.back();
  });

  // Ensure product versions are loaded for the default product shown in
  // Product list.
  if (jQ('#id_product').length && !jQ('#id_product_version').val()) {
    fireEvent(jQ('#id_product')[0],'change');
  }
};

Nitrate.TestPlans.Edit.on_load = function() {
  jQ('#env_group_help_link').on('click', function(t) {
    jQ('#env_group_help').toggle();
  });
  jQ('#env_group_help_close').on('click', function(t) {
    jQ('#env_group_help').hide();
  });
  bind_version_selector_to_product(false);

  jQ('.js-back-button').on('click', function() {
    window.location.href = jQ(this).data('param');
  });
};

Nitrate.TestPlans.Advance_Search_List.on_load = function() {
  if (jQ('#id_product').length) {
    bind_version_selector_to_product(true);
  }

  if (jQ('#id_check_all_plans').length) {
    jQ('#id_check_all_plans').on('click', function(e) {
      clickedSelectAll(this, jQ('#plans_form')[0], 'plan');
      if (this.checked) {
        jQ('#plan_advance_printable').attr('disabled', false);
      } else {
        jQ('#plan_advance_printable').attr('disabled', true);
      }
    });
  }

  if (jQ('#column_add').length) {
    jQ('#column_add').on('change', function(t) {
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

  jQ('input[name="plan_id"]').on('click', function(t) {
    if (this.checked) {
      jQ(this).parent().parent().addClass('selection_row');
    } else {
      jQ(this).parent().parent().removeClass('selection_row');
    }
  });

  jQ("input[type=checkbox][name=plan]").on('click', function(){
    if(jQ("input[type=checkbox][name=plan]:checked").length) {
      jQ('#plan_advance_printable').attr('disabled', false);
    } else {
      jQ('#plan_advance_printable').attr('disabled', true);
    }
  });

  jQ('.js-new-plan').on('click', function() {
    window.location = jQ(this).data('param');
  });
  jQ('.js-clone-plan').on('click', function() {
    postToURL(jQ(this).data('param'), Nitrate.Utils.formSerialize(this.form), 'get');
  });
  jQ('#plan_advance_printable').on('click', function() {
    postToURL(jQ(this).data('param'), Nitrate.Utils.formSerialize(this.form), 'get');
  });
  jQ('.js-export-cases').on('click', function() {
    postToURL(jQ(this).data('param'), Nitrate.Utils.formSerialize(this.form), 'get');
  });
};

Nitrate.TestPlans.List.on_load = function() {
  if (jQ('#id_product').length) {
    bind_version_selector_to_product(true);
  }

  if (jQ('#id_check_all_plans').length) {
    jQ('#id_check_all_plans').on('click', function(e) {
      clickedSelectAll(this, jQ('#plans_form')[0], 'plan');
      if (this.checked) {
        jQ('#plan_list_printable').attr('disabled', false);
      } else {
        jQ('#plan_list_printable').attr('disabled', true);
      }
    });
  }

  if (jQ('#column_add').length) {
    jQ('#column_add').on('change', function(t) {
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

  jQ('input[name="plan_id"]').on('click', function(t) {
    if (this.checked) {
      jQ(this).parent().parent().addClass('selection_row');
    } else {
      jQ(this).parent().parent().removeClass('selection_row');
    }
  });

  if (jQ('#testplans_table').length) {
    jQ('#testplans_table').dataTable({
      "iDisplayLength": 20,
      "sPaginationType": "full_numbers",
      "bFilter": false,
      // "bLengthChange": false,
      "aLengthMenu": [[10, 20, 50, -1], [10, 20, 50, "All"]],
      "aaSorting": [[ 1, "desc" ]],
      "bProcessing": true,
      "bServerSide": true,
      "sAjaxSource": "/plans/ajax/"+this.window.location.search,
      "aoColumns": [
        {"bSortable": false },
        null,
        {"sType": "html"},
        {"sType": "html"},
        {"sType": "html"},
        null,
        {"bVisible": false},
        null,
        {"bSortable": false },
        {"bSortable": false },
        {"bSortable": false }
      ]
    });
  }
  jQ("#testplans_table tbody tr input[type=checkbox][name=plan]").on("click", function() {
    if (jQ("input[type=checkbox][name=plan]:checked").length) {
      jQ('#plan_list_printable').attr('disabled', false);
    } else {
      jQ('#plan_list_printable').attr('disabled', true);
    }
  });

  jQ('.js-new-plan').on('click', function() {
    window.location = jQ(this).data('param');
  });
  jQ('.js-clone-plan').on('click', function() {
    postToURL(jQ(this).data('param'), Nitrate.Utils.formSerialize(this.form), 'get');
  });
  jQ('#plan_list_printable').on('click', function() {
    postToURL(jQ(this).data('param'), Nitrate.Utils.formSerialize(this.form), 'get');
  });
  jQ('.js-export-cases').on('click', function() {
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
  'getTabContentContainer': function(options) {
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
  'loadPlansTreeView': function(plan_id) {
    // Initial the tree view
    Nitrate.TestPlans.TreeView.init(plan_id);
    Nitrate.TestPlans.TreeView.render_page();
  },
  'initTabs': function() {
    jQ('li.tab a').on('click', function(i) {
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
      .map(function(index, element) {
        return element.getAttribute('href');
      })
      .filter(function(index, element) {
        return element === switchTo;
      }).length > 0;
    if (!exist) {
      switchTo = defaultSwitchTo;
    }
    fireEvent(jQ('a[href=\"' + switchTo + '\"]')[0], 'click');
  },
  /*
   * Load cases table.
   *
   * Proxy of global function with same name.
   */
  'loadCases': function(container, plan_id, parameters) {
    constructPlanDetailsCasesZone(container, plan_id, parameters);

    if (Nitrate.TestPlans.Details._bindEventsOnLoadedCases === undefined) {
      Nitrate.TestPlans.Details._bindEventsOnLoadedCases = bindEventsOnLoadedCases({
        'cases_container': container,
        'plan_id': plan_id,
        'parameters': parameters
      });
    }
  },
  // Loading newly created cases with proposal status to show table of these kind of cases.
  'loadConfirmedCases': function(plan_id) {
    let container = Nitrate.TestPlans.CasesContainer.ConfirmedCases;
    Nitrate.TestPlans.Details.loadCases(container, plan_id, {
      'a': 'initial',
      'template_type': 'case',
      'from_plan': plan_id
    });
  },
  // Loading reviewing cases to show table of these kind of cases.
  'loadReviewingCases': function(plan_id) {
    let container = Nitrate.TestPlans.CasesContainer.ReviewingCases;
    Nitrate.TestPlans.Details.loadCases(container, plan_id, {
      'a': 'initial',
      'template_type': 'review_case',
      'from_plan': plan_id
    });
  },
  'bindEventsOnLoadedCases': function(container) {
    let elem = typeof container === 'string' ? jQ('#' + container) : jQ(container);
    let form = elem.children()[0];
    let table = elem.children()[1];
    Nitrate.TestPlans.Details._bindEventsOnLoadedCases(table, form);
  },
  'observeEvents': function(plan_id) {
    let NTPD = Nitrate.TestPlans.Details;

    jQ('#tab_testcases').on('click', function(e) {
      if (!NTPD.testcasesTabOpened) {
        NTPD.loadConfirmedCases(plan_id);
        NTPD.testcasesTabOpened = true;
      }
    });

    jQ('#tab_treeview').on('click', function(e) {
      if (!NTPD.plansTreeViewOpened) {
        NTPD.loadPlansTreeView(plan_id);
        NTPD.plansTreeViewOpened = true;
      }
    });

    jQ('#tab_reviewcases').on('click', function(e) {
      if (!Nitrate.TestPlans.Details.reviewingCasesTabOpened) {
        Nitrate.TestPlans.Details.loadReviewingCases(plan_id);
        Nitrate.TestPlans.Details.reviewingCasesTabOpened = true;
      }
    });

    // Initial the enable/disble btns
    if (jQ('#btn_disable').length) {
      jQ('#btn_disable').on('click', function(e){
        updateObject('testplans.testplan', plan_id, 'is_active', 'False', 'bool');
      });
    }

    if (jQ('#btn_enable').length) {
      jQ('#btn_enable').on('click', function(e) {
        updateObject('testplans.testplan', plan_id, 'is_active', 'True', 'bool');
      });
    }
  },
  'reopenCasesTabThen': function() {
    Nitrate.TestPlans.Details.testcasesTabOpened = false;
  },
  'reopenReviewingCasesTabThen': function() {
    Nitrate.TestPlans.Details.reviewingCasesTabOpened = false;
  },
  /*
   * Helper function to reopen other tabs.
   *
   * Arguments:
   * - container: a jQuery object, where the operation happens to reopen other tabs. The container
   *              Id is used to select the reopen operations.
   */
  'reopenTabHelper': function(container) {
    let switchMap = {
      'testcases': function() {
        Nitrate.TestPlans.Details.reopenReviewingCasesTabThen();
      },
      'reviewcases': function() {
        Nitrate.TestPlans.Details.reopenCasesTabThen();
      }
    };
    switchMap[container.attr('id')]();
  },
  'on_load': function() {
    let plan_id = Nitrate.TestPlans.Instance.pk;

    // Initial the contents
    constructTagZone(jQ('#tag')[0], { plan: plan_id });
    constructPlanComponentsZone('components');

    Nitrate.TestPlans.Details.observeEvents(plan_id);
    Nitrate.TestPlans.Details.initTabs();

    // Make the import case dialog draggable.
    jQ('#id_import_case_zone').draggable({ containment: '#content' });

    // Bind for run form
    jQ('#id_form_run').on('submit', function(e) {
      if (!Nitrate.Utils.formSerialize(this).run) {
        e.stopPropagation();
        e.preventDefault();
        window.alert(default_messages.alert.no_run_selected);
      }
    });

    jQ('#id_check_all_runs').on('click', function(e) {
      clickedSelectAll(this, jQ('#testruns_table')[0], 'run');
    });

    Nitrate.Utils.enableShiftSelectOnCheckbox('case_selector');
    Nitrate.Utils.enableShiftSelectOnCheckbox('run_selector');

    Nitrate.TestPlans.Runs.initializeRunTab();
    Nitrate.TestPlans.Runs.bind();

    jQ('#btn_edit').on('click', function() {
      window.location.href = jQ(this).data('param');
    });
    jQ('#btn_clone, #btn_export, #btn_print').on('click', function() {
      let params = jQ(this).data('params');
      window.location.href = params[0] + '?plan=' + params[1];
    });
    jQ('#id_import_case_zone').find('.js-close-zone').on('click', function() {
      jQ('#id_import_case_zone').hide();
      jQ('#import-error').empty();
    });
    jQ('.js-del-attach').on('click', function() {
      let params = jQ(this).data('params');
      deleConfirm(params[0], 'from_plan', params[1]);
    });

    let treeview = jQ('#treeview')[0];
    let planPK = parseInt(jQ('#id_tree_container').data('param'));

    jQ('#js-change-parent-node').on('click', function() {
      Nitrate.TestPlans.TreeView.changeParentPlan(treeview, planPK);
    });
    jQ('#js-add-child-node').on('click', function() {
      Nitrate.TestPlans.TreeView.addChildPlan(treeview, planPK);
    });
    jQ('#js-remove-child-node').on('click', function() {
      Nitrate.TestPlans.TreeView.removeChildPlan(treeview, planPK);
    });
  }
};

Nitrate.TestPlans.SearchCase.on_load = function() {
  if (jQ('#id_product').length) {
    if (jQ('#id_product').val() !== "") {
      bind_category_selector_to_product(true, true, jQ('#id_product')[0], jQ('#id_category')[0]);
      bind_component_selector_to_product(true, true, jQ('#id_product')[0], jQ('#id_component')[0]);
    }
  }
  // new feature for searching by case id.
  let quick_search = jQ("#tp_quick_search_cases_form");
  let normal_search = jQ("#tp_advanced_search_case_form");
  let quick_tab = jQ("#quick_tab");
  let normal_tab = jQ("#normal_tab");
  let search_mode = jQ("#search_mode");
  let errors = jQ(".errors");
  let triggerFormDisplay = function(options) {
    options.show.show();
    options.show_tab.addClass("profile_tab_active");
    options.hide.hide();
    options.hide_tab.removeClass("profile_tab_active");
  };

  jQ("#quick_search_cases").on("click", function() {
    // clear errors
    errors.empty();
    search_mode.val("quick");
    triggerFormDisplay({
      "show": quick_search,
      "show_tab": quick_tab,
      "hide": normal_search,
      "hide_tab": normal_tab
    });
  });
  jQ("#advanced_search_cases").on("click", function() {
    // clear errors
    errors.empty();
    search_mode.val("normal");
    triggerFormDisplay({
      "show": normal_search,
      "show_tab": normal_tab,
      "hide": quick_search,
      "hide_tab": quick_tab
    });
  });

  if (jQ('#id_table_cases').length) {
    jQ('#id_table_cases').dataTable({
      "aoColumnDefs":[{ "bSortable":false, "aTargets":[ 'nosort' ] }],
      "aaSorting": [[ 1, "desc" ]],
      "sPaginationType": "full_numbers",
      "bFilter": false,
      "aLengthMenu": [[10, 20, 50, -1], [10, 20, 50, "All"]],
      "iDisplayLength": 20,
      "bProcessing": true
    });
  }

  if (jQ("#id_checkbox_all_cases").length) {
    bindSelectAllCheckbox(jQ('#id_checkbox_all_cases')[0], jQ('#id_form_cases')[0], 'case');
  }
};

Nitrate.TestPlans.Clone.on_load = function() {
  bind_version_selector_to_product(false);

  jQ('#id_link_testcases').on('change', function(e) {
    if (this.checked) {
      this.parentNode.parentNode.className = 'choose';
      jQ('#id_clone_case_zone')[0].style.display = 'block';
    } else {
      this.parentNode.parentNode.className = 'unchoose';
      jQ('#id_clone_case_zone')[0].style.display = 'none';
    }
  });

  jQ('#id_copy_testcases').on('change', function(e) {
    if (this.checked) {
      jQ('#id_maintain_case_orignal_author')[0].disabled = false;
      jQ('#id_keep_case_default_tester')[0].disabled = false;
    } else {
      jQ('#id_maintain_case_orignal_author')[0].disabled = true;
      jQ('#id_keep_case_default_tester')[0].disabled = true;
    }
  });
  // Populate product version field.
  if (jQ('#id_product').length && !jQ('#id_product_version').val()) {
    fireEvent(jQ('#id_product')[0],'change');
  }

  jQ('.js-cancel-button').on('click', function() {
    window.history.back();
  });
};

Nitrate.TestPlans.Attachment.on_load = function() {
  jQ(document).ready(function() {
    jQ("#upload_file").change(function () {
      let iSize = jQ("#upload_file")[0].files[0].size;
      let limit = parseInt(jQ('#upload_file').attr('limit'));

      if (iSize > limit) {
        window.alert("Your attachment's size is beyond limit, please limit your attachments to under 5 megabytes (MB).");
      }
    });

    jQ('.js-back-button').on('click', function() {
      window.history.go(-1);
    });

    jQ('.js-del-attach').on('click', function() {
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

function showShortSummary() {
  jQ('#id_link_show_more').show();
  jQ('#display_summary').hide();
  if (jQ('#display_summary_short').length) {
    jQ('#id_link_show_short').hide();
    jQ('#display_summary_short').show();
  }

  window.scrollTo(0, 0);
}

/**
 * Unlink selected cases from current TestPlan.
 *
 * Rewrite function unlinkCasePlan to avoid conflict. Remove it when confirm it's not used any more.
 */
function unlinkCasesFromPlan(container, form, table) {
  let selectedCaseIDs = getSelectedCaseIDs(table);
  if (selectedCaseIDs.length === 0)
    return;
  if (! confirm("Are you sure you want to remove test case(s) from this test plan?")) {
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

function toggleTestCasePane(options, callback) {
  let casePaneContainer = options.casePaneContainer;

  // If any of these is invalid, just keep quiet and don't display anything.
  if (options.case_id === undefined || casePaneContainer === undefined) {
    return;
  }

  casePaneContainer.toggle();

  if (casePaneContainer.find('.ajax_loading').length) {
    sendHTMLRequest({
      url: '/case/' + options.case_id + '/readonly-pane/',
      container: casePaneContainer,
      callbackAfterFillIn: callback
    });
  }

}

// TODO: merge this function with above
function toggleTestCaseReviewPane(options) {
  let casePaneContainer = options.casePaneContainer;

  // If any of these is invalid, just keep quiet and don't display anything.
  if (options.case_id === undefined || casePaneContainer === undefined) {
    return;
  }

  casePaneContainer.toggle();

  if (casePaneContainer.find('.ajax_loading').length) {
    sendHTMLRequest({
      url: '/case/' + options.case_id + '/review-pane/',
      container: casePaneContainer,
      callbackAfterFillIn: options.callback
    });
  }
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
  let plan_id = options.plan_id;
  let cases_container = options.cases_container;

  return function(container, form) {
    //jQ(cases_container)
      //.find('.js-cases-list').find('input[name="case"]')
      //.on('click', function(e) {
        //Nitrate.TestPlans.Details.refreshCasesSelectionCheck(jQ(cases_container));
      //});

    // Observe the change sortkey
    jQ(container).parent().find('.case_sortkey.js-just-loaded').on('click', function(e) {
      changeCaseOrder({'testcaseplan': jQ(this).next().html(), 'sortkey': jQ(this).html()}, function () {
        constructPlanDetailsCasesZone(cases_container, plan_id, parameters);
      });
    });

    jQ(container).parent().find('.change_status_selector.js-just-loaded').on('change', function(e) {
      let be_confirmed = (parseInt(this.value) === 2);
      let was_confirmed = (jQ(this).parent()[0].attributes.status.value === "CONFIRMED");
      let case_id = jQ(this).parent().parent()[0].id;
      changeTestCaseStatus(plan_id, this, case_id, be_confirmed, was_confirmed);
    });

    // Display/Hide the case content
    jQ(container).parent().find('.expandable.js-just-loaded').on('click', function(e) {
      let btn = this;
      let title = jQ(this).parent()[0]; // Container
      let content = jQ(this).parent().next()[0]; // Content Containers
      let case_id = title.id;
      let template_type = jQ(form).parent().find('input[name="template_type"]')[0].value;

      if (template_type === 'case') {
        toggleTestCasePane({ 'case_id': case_id, 'casePaneContainer': jQ(content) });
        toggleExpandArrow({ 'caseRowContainer': jQ(title), 'expandPaneContainer': jQ(content) });
        return;
      }

      // Review case content call back;
      let review_case_content_callback = function(e) {
        let comment_container_t = jQ('<div>')[0];

        // Change status/comment callback
        jQ(content).parent().find('.update_form').unbind('submit').on('submit', function (e) {
          e.stopPropagation();
          e.preventDefault();

          let params = Nitrate.Utils.formSerialize(this);
          submitComment(comment_container_t, params, function () {
            let td = jQ('<td>', {colspan: 12});
            td.append(getAjaxLoading('id_loading_' + params.object_pk));
            jQ(content).html(td);
            // FIXME: Why trigger twice? Remove one if it's doable.
            fireEvent(btn, 'click');
            fireEvent(btn, 'click');
          });
        });

        // Observe the delete comment form
        jQ(content).parent().find('.form_comment').off('submit').on('submit', function (e) {
          e.stopPropagation();
          e.preventDefault();

          if (!window.confirm(default_messages.confirm.remove_comment)) {
            return false;
          }
          // Every comment form has a hidden input with name object_pk to associate with the case.
          let caseId = Nitrate.Utils.formSerialize(this).object_pk;
          removeComment(this, function () {
            let td = jQ('<td>', {colspan: 12});
            td.append(getAjaxLoading('id_loading_' + caseId));
            jQ(content).html(td);
            fireEvent(btn, 'click');
            fireEvent(btn, 'click');
          });
        });
      };

      let case_content_callback = null;
      switch(template_type) {
        case 'review_case':
          case_content_callback = review_case_content_callback;
          break;
        default:
          case_content_callback = function(e) {};
      }

      toggleTestCaseReviewPane({
        'case_id': case_id,
        'casePaneContainer': jQ(content),
        'callback': case_content_callback
      });
      toggleExpandArrow({ 'caseRowContainer': jQ(title), 'expandPaneContainer': jQ(content) });
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

  return function(e) {
    let selectedCaseIDs = getSelectedCaseIDs(options.table);
    if (selectedCaseIDs.length === 0) {
      window.alert(default_messages.alert.no_case_selected);
      return false;
    }
    let status_pk = this.value;
    if (!status_pk) {
      return false;
    }
    if (! window.confirm(default_messages.confirm.change_case_status)) {
      return false;
    }

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
        'new_value': status_pk
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
  };
}


/*
 * Event handler invoked when TestCases' Priority is changed.
 */
function onTestCasePriorityChange(options) {
  let container = options.container;

  return function(e) {
    let selectedCaseIDs = getSelectedCaseIDs(options.table);
    if (selectedCaseIDs.length === 0) {
      window.alert(default_messages.alert.no_case_selected);
      return false;
    }
    // FIXME: how about show a message to user to let user know what is happening?
    if (!this.value) {
      return false;
    }
    if (! window.confirm(default_messages.confirm.change_case_priority)) {
      return false;
    }

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
        new_value: this.value
      },
      traditional: true,
      success: function () {
        constructPlanDetailsCasesZone(container, options.planId, postdata);
      },
    });
  };
}


/*
 * Event handler invoked when TestCases' Automated is changed.
 */
function onTestCaseAutomatedClick(options) {
  let container = options.container;

  return function(e) {
    let selectedCaseIDs = getSelectedCaseIDs(options.table);
    if (selectedCaseIDs.length === 0) {
      window.alert(default_messages.alert.no_case_selected);
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

  return function(response) {
    let dialog = getDialog();
    clearDialog(dialog);

    let returnobj = jQ.parseJSON(response.responseText);

    let template = Handlebars.compile(jQ('#batch_tag_summary_template').html());
    jQ(dialog).html(template({'tags': returnobj}))
      .find('.js-close-button').on('click', function() {
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
  return function(e) {
    let selectedCaseIDs = getSelectedCaseIDs(options.table);
    if (selectedCaseIDs.length === 0) {
      window.alert(default_messages.alert.no_case_selected);
      return false;
    }

    constructBatchTagProcessDialog(options.planId);

    // Observe the batch tag form submit
    jQ('#id_batch_tag_form').on('submit', function(e) {
      e.stopPropagation();
      e.preventDefault();

      let tagData = Nitrate.Utils.formSerialize(this);
      if (!tagData.tags) {
        return false;
      }
      let params = serializeFormData({
        'form': options.form,
        'zoneContainer': options.container,
        'selectedCaseIDs': selectedCaseIDs,
        'hashable': true
      });
      params.tags = tagData.tags;

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
      addBatchTag(params, callback, 'serialized');
    });
  };
}

function onTestCaseTagDeleteClick(options) {
  let parameters = options.parameters;

  return function(e) {
    let c = getDialog();
    let selectedCaseIDs = getSelectedCaseIDs(options.table);
    if (selectedCaseIDs.length === 0) {
      window.alert(default_messages.alert.no_case_selected);
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

/*
 * To change selected cases' sort number.
 */
function onTestCaseSortNumberClick(options) {
  return function(e) {
    // NOTE: new implementation does not use testcaseplan.pk
    let selectedCaseIDs = getSelectedCaseIDs(options.table);
    if (selectedCaseIDs.length === 0) {
      window.alert(default_messages.alert.no_case_selected);
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

/*
 * To change selected cases' category.
 */
function onTestCaseCategoryClick(options) {
  let container = options.container;
  let parameters = options.parameters;

  return function(e) {
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
      window.alert(default_messages.alert.no_case_selected);
      return false;
    }

    renderCategoryForm(c, params, function (e) {
      e.stopPropagation();
      e.preventDefault();

      let selectedCaseIDs = getSelectedCaseIDs(options.table);
      if (selectedCaseIDs.length === 0) {
        window.alert(default_messages.alert.no_case_selected);
        return false;
      }

      let params = serializeFormData({
        'form': this,
        'zoneContainer': container,
        'selectedCaseIDs': selectedCaseIDs
      });
      if (params.indexOf('o_category') < 0) {
        window.alert(default_messages.alert.no_category_selected);
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
  return function(e) {
    let selectedCaseIDs = getSelectedCaseIDs(options.table);
    if (selectedCaseIDs.length === 0) {
      window.alert(default_messages.alert.no_case_selected);
      return false;
    }

    let email_or_username = window.prompt('Please type new email or username');
    if (!email_or_username) {
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
        new_value: email_or_username
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

  return function(e) {
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
      window.alert(default_messages.alert.no_case_selected);
      return false;
    }

    renderComponentForm(c, params, function (e) {
      e.stopPropagation();
      e.preventDefault();

      let selectedCaseIDs = getSelectedCaseIDs(options.table);
      if (selectedCaseIDs.length === 0) {
        window.alert(default_messages.alert.no_case_selected);
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

  return function(e) {
    let selectedCaseIDs = getSelectedCaseIDs(options.table);
    if (selectedCaseIDs.length === 0) {
      window.alert(default_messages.alert.no_case_selected);
      return false;
    }

    let email_or_username = window.prompt('Please type new email or username');
    if (!email_or_username) {
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
        new_value: email_or_username
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
  let plan_id = options.planId;
  let parameters = options.parameters;

  return function(response) {
    let form = jQ(container).children()[0];
    let table = jQ(container).children()[1];

    // Presume the first form element is the form
    if (form.tagName !== 'FORM') {
      window.alert('form element of container is not a form');
      return false;
    }

    let filter = jQ(form).parent().find('.list_filter')[0];

    // Filter cases
    jQ(form).on('submit', function(e) {
      e.stopPropagation();
      e.preventDefault();
      constructPlanDetailsCasesZone(container, plan_id, Nitrate.Utils.formSerialize(form));
    });

    // Change the case backgroud after selected
    jQ(form).parent().find('input[name="case"]').on('click', function(e) {
      if (this.checked) {
        jQ(this).parent().parent().addClass('selection_row');
      } else {
        jQ(this).parent().parent().removeClass('selection_row');
      }
    });

    // Observe the check all selectbox
    if (jQ(form).parent().find('input[value="all"]').length) {
      let element = jQ(form).parent().find('input[value="all"]')[0];
      jQ(element).on('click', function(e) {
        clickedSelectAll(this, jQ(this).closest('.tab_list')[0], 'case');
      });
    }

    if (jQ(form).parent().find('.btn_filter').length) {
      let element = jQ(form).parent().find('.btn_filter')[0];
      jQ(element).on('click', function(t) {
        if (filter.style.display === 'none') {
          jQ(filter).show();
          jQ(this).html(default_messages.link.hide_filter);
        } else {
          jQ(filter).hide();
          jQ(this).html(default_messages.link.show_filter);
        }
      });
    }

    // Bind click the tags in tags list to tags field in filter
    if (jQ(form).parent().find('.taglist a[href="#testcases"]').length) {
      jQ(form).parent().find('.taglist a').on('click', function(e) {
        if (filter.style.display === 'none') {
          fireEvent(jQ(form).parent().find('.filtercase')[0], 'click');
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
      jQ(element).on('click', function(e) {
        let params = Nitrate.Utils.formSerialize(form);
        params.case = getSelectedCaseIDs(table);
        resortCasesDragAndDrop(container, this, form, table, params, function (responseData) {
          params.a = 'initial';
          constructPlanDetailsCasesZone(container, plan_id, params);
        });
      });
    }

    // Bind batch change case status selector
    let element = jQ(form).parent().find('input[name="new_case_status_id"]')[0];
    if (element !== undefined) {
      jQ(element).on('change', onTestCaseStatusChange({
        'form': form, 'table': table, 'container': container, 'planId': plan_id
      }));
    }

    element = jQ(form).parent().find('input[name="new_priority_id"]')[0];
    if (element !== undefined) {
      jQ(element).on('change', onTestCasePriorityChange({
        'form': form, 'table': table, 'container': container, 'planId': plan_id
      }));
    }

    // Observe the batch case automated status button
    element = jQ(form).parent().find('input.btn_automated')[0];
    if (element !== undefined) {
      jQ(element).on('click', onTestCaseAutomatedClick({
        'form': form, 'table': table, 'container': container, 'planId': plan_id
      }));
    }

    element = jQ(form).parent().find('input.btn_component')[0];
    if (element !== undefined) {
      jQ(element).on('click', onTestCaseComponentClick({
        'container': container, 'form': form, 'planId': plan_id, 'table': table, 'parameters': parameters
      }));
    }

    element = jQ(form).parent().find('input.btn_category')[0];
    if (element !== undefined) {
      jQ(element).on('click', onTestCaseCategoryClick({
        'container': container, 'form': form, 'planId': plan_id, 'table': table, 'parameters': parameters
      }));
    }

    element = jQ(form).parent().find('input.btn_default_tester')[0];
    if (element !== undefined) {
      jQ(element).on('click', onTestCaseDefaultTesterClick({
        'container': container, 'form': form, 'planId': plan_id, 'table': table
      }));
    }

    element = jQ(form).parent().find('input.sort_list')[0];
    if (element !== undefined) {
      jQ(element).on('click', onTestCaseSortNumberClick({
        'container': container, 'form': form, 'planId': plan_id, 'table': table
      }));
    }

    element = jQ(form).parent().find('input.btn_reviewer')[0];
    if (element !== undefined) {
      jQ(element).on('click', onTestCaseReviewerClick({
        'container': container, 'form': form, 'planId': plan_id, 'table': table, 'parameters': parameters
      }));
    }

    // Observe the batch add case button
    element = jQ(form).parent().find('input.tag_add')[0];
    if (element !== undefined) {
      jQ(element).on('click', onTestCaseTagAddClick({
        'container': container, 'form': form, 'planId': plan_id, 'table': table
      }));
    }

    // Observe the batch remove tag function
    element = jQ(form).parent().find('input.tag_delete')[0];
    if (element !== undefined) {
      jQ(element).on('click', onTestCaseTagDeleteClick({
        'container': container, 'form': form, 'planId': plan_id, 'table': table, 'parameters': parameters
      }));
    }

    bindEventsOnLoadedCases(
      {'cases_container': container, 'plan_id': plan_id, 'parameters': parameters}
    )(table, form);
  };
}


function constructPlanDetailsCasesZone(container, plan_id, parameters) {
  container = typeof container === 'string' ? jQ('#' + container)[0] : container;
  jQ(container).html('<div class="ajax_loading"></div>');
  let postData = parameters || {a: 'initial', from_plan: plan_id};
  postHTMLRequest({
    url: '/cases/',
    data: postData,
    traditional: true,
    container: container,
    callbackAfterFillIn: function () {
      jQ('.show_change_status_link').on('click', function() {
        jQ(this).hide().next().show();
      });

      let type = typeof parameters.template_type === 'string' ?
        (parameters.template_type === 'case') ? '-' : '-review-' :
        (parameters.template_type[0] === 'case') ? '-' : '-review-';
      let casesSection = (type === '-') ? jQ('#testcases')[0] : jQ('#reviewcases')[0];
      let casesTable = jQ(casesSection).find('.js-cases-list')[0];
      let navForm = jQ('#js' + type + 'cases-nav-form')[0];

      jQ('#js' + type + 'case-menu, #js' + type + 'new-case').on('click', function() {
        let params = jQ(this).data('params');
        window.location.href = params[0] + '?from_plan=' + params[1];
      });
      jQ('#js' + type + 'import-case').on('click', function() {
        jQ('#id_import_case_zone').toggle();
      });
      jQ('#js' + type + 'add-case-to-plan').on('click', function() {
        window.location.href = jQ(this).data('param');
      });
      jQ('#js' + type + 'export-case').on('click', function() {
        submitSelectedCaseIDs(jQ(this).data('param'), casesTable);
      });
      jQ('#js' + type + 'print-case').on('click', function() {
        submitSelectedCaseIDs(jQ(this).data('param'), casesTable);
      });
      jQ('#js' + type + 'clone-case').on('click', function() {
        postToURL(jQ(this).data('param'), {
            from_plan: Nitrate.Utils.formSerialize(navForm).from_plan,
            case: getSelectedCaseIDs(casesTable)
          },
          'get');
      });
      jQ('#js' + type + 'remove-case').on('click', function() {
        unlinkCasesFromPlan(casesSection, navForm, casesTable);
      });
      jQ('#js' + type + 'new-run').on('click', function() {
        postToURL(jQ(this).data('param'), {
          from_plan: Nitrate.Utils.formSerialize(navForm).from_plan,
          case: getSelectedCaseIDs(casesTable)
        });
      });
      jQ('#js' + type + 'add-case-to-run').on('click', function() {
        postToURL(jQ(this).data('param'), {case: getSelectedCaseIDs(casesTable)}, 'get');
      });
      jQ('.js' + type + 'status-item').on('click', function() {
        this.form.new_case_status_id.value = jQ(this).data('param');
        fireEvent(this.form.new_case_status_id, 'change');
      });
      jQ('.js' + type + 'priority-item').on('click', function() {
        this.form.new_priority_id.value = jQ(this).data('param');
        fireEvent(this.form.new_priority_id, 'change');
      });
      let $toggleAllCasesButton = (type === '-') ? jQ('#id_blind_all_link') : jQ('#review_id_blind_all_link');
      $toggleAllCasesButton.find('.collapse-all').on('click', function() {
        toggleAllCases(this);
      });
      jQ(casesTable).find('.js' + type + 'case-field').on('click', function() {
        sortCase(casesSection, jQ(this).parents('thead').data('param'), jQ(this).data('param'));
      });

      /* @function */
      let func = constructPlanDetailsCasesZoneCallback({
        'container': container,
        'planId': plan_id,
        'parameters': postData
      });
      func();
    },
  });
}

function constructPlanComponentsZone(container, parameters, callback) {
  container =
    typeof container === 'string' ? jQ('#' + container) : container;

  let url = Nitrate.http.URLConf.reverse({ name: 'plan_components' });

  let complete = function() {
    if (callback) {
      callback();
    }

    jQ('#id_form_plan_components').on('submit', function(e) {
      e.stopPropagation();
      e.preventDefault();
      let p = Nitrate.Utils.formSerialize(this);
      let submitButton = jQ(this).find(':submit')[0];
      p[submitButton.name] = submitButton.value;
      constructPlanComponentsZone(container, p, callback);
    });

    jQ('.link_remove_plan_component').on('click', function(e) {
      let c = confirm(default_messages.confirm.remove_case_component);
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

    jQ('#id_checkbox_all_component').on('click', function(e) {
      clickedSelectAll(this, jQ(this).closest('form')[0], 'component');
    });

    jQ('.js-update-components').click(function() {
      constructPlanComponentModificationDialog();
    });

    let c_count = jQ('tbody#component').attr('count');
    jQ('#component_count').text(c_count);
  };

  sendHTMLRequest({
    url: url,
    data: parameters || {plan: Nitrate.TestPlans.Instance.pk},
    traditional: true,
    container: container,
    callbackAfterFillIn: complete,
  });
}

function constructPlanComponentModificationDialog(container) {
  container = container || getDialog();
  jQ(container).show();

  let d = jQ('<div>');
  let parameters = { a: 'get_form', plan: Nitrate.TestPlans.Instance.pk };
  let callback = function(t) {
    let action = Nitrate.http.URLConf.reverse({ name: 'plan_components' });
    let form_observe = function(e) {
      e.stopPropagation();
      e.preventDefault();
      let submitButton = jQ(this).find(':submit')[0];
      constructPlanComponentsZone(
        'components',
        jQ(this).serialize() + '&' + submitButton.name + '=' + submitButton.value
      );
      clearDialog();
    };
    let notice = 'Press "Ctrl" to select multiple default component';
    let s = jQ('<input>', {'type': 'submit', 'name': 'a', 'value': 'Update'});

    let f = constructForm(d.html(), action, form_observe, notice, s[0]);
    jQ(container).html(f);
  };

  // Get the form and insert into the dialog.
  constructPlanComponentsZone(d[0], parameters, callback);
}

function constructBatchTagProcessDialog(plan_id) {
  let template = Handlebars.compile(jQ('#batch_tag_form_template').html());
  jQ('#dialog').html(template())
    .find('.js-cancel-button').on('click', function() {
      jQ('#dialog').hide();
    })
    .end().show();
  // Bind the autocomplete for tags
  jQ('#add_tag_plan').autocomplete({
    'minLength': 2,
    'appendTo': '#id_batch_add_tags_autocomplete',
    'source': function(request, response) {
      sendHTMLRequest({
        url: '/management/getinfo/',
        data: {
          'name__startswith': request.term,
          'info_type': 'tags',
          'format': 'ulli',
          'cases__plan__pk': plan_id,
          'field': 'name'
        },
        success: function (data) {
          let processedData = [];
          if (data.indexOf('<li>') > -1) {
            processedData = data.slice(data.indexOf('<li>') + 4, data.lastIndexOf('</li>'))
            .split('<li>').join('').split('</li>');
          }
          response(processedData);
        }
      });
    },
  });
}

function sortCase(container, plan_id, order) {
  let form = jQ(container).children()[0];
  let parameters = Nitrate.Utils.formSerialize(form);
  parameters.a = 'sort';

  if (parameters.case_sort_by === order) {
    parameters.case_sort_by = '-' + order;
  } else {
    parameters.case_sort_by = order;
  }
  constructPlanDetailsCasesZone(container, plan_id, parameters);
}

function changeCaseMember(parameters, callback) {
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
    jQ(form).parent().find('.change_status_selector').each(function(t) {
      let w = this.selectedIndex;
      jQ(this).replaceWith((jQ('<span>')).html(this.options[w].text));
    });

    // init the tableDnD object
    new TableDnD().init(table);
    button.innerHTML = 'Done Sorting';
    jQ(table).parent().find('tr').addClass('cursor_move');
  } else {
    jQ(button).replaceWith((jQ('<span>')).html('...Submitting changes'));

    jQ(table).parent().find('input[type=checkbox]').each(function(t) {
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
  let tab_name = element.hash.slice(1);
  jQ('#tab_treeview').removeClass('tab_focus');
  jQ('#treeview').hide();
  jQ('#tab_' + tab_name).addClass('tab_focus').children('a').click();
  jQ('#' + tab_name).show();
}

function expandCurrentPlan(element) {
  let tree = Nitrate.TestPlans.TreeView;

  if (jQ(element).find('.collapse_icon').length) {
    let e_container = jQ(element).find('.collapse_icon');
    let li_container = e_container.parent().parent();
    let e_pk = e_container.next('a').html();
    let obj = tree.traverse(tree.data, e_pk);

    if (typeof obj.children !== 'object' || obj.children === []) {
      tree.filter({parent__pk: e_pk}, function (responseData) {
        let objs = Nitrate.Utils.convert('obj_to_list', responseData);
        tree.insert(obj, objs);
        li_container.append(tree.render(objs));
      });
    }

    li_container.find('ul').first().show();
    e_container.attr('src', '/static/images/t2.gif')
      .removeClass('collapse_icon').addClass('expand_icon');
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
  'render': function (data, textStatus, jqXHR) {
    let tbody = jQ('#testruns_body');
    let html = jQ(data.html);
    let btnCheckAll = jQ('#box_select_rest input:checkbox');
    if (btnCheckAll.length > 0 && btnCheckAll.is(':checked')) {
      html.find('.run_selector').attr('checked', 'checked');
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
          "aoColumnDefs":[
            { "bSortable": false, "aTargets":[0, 8, 9, 10] },
            { "sType": "numeric", "aTargets": [1, 6, 8, 9, 10 ] },
            { "sType": "date", "aTargets": [5] }
          ],
          'bSort': true,
          'bProcessing': true,
          'bFilter': false,
          "bLengthChange": false,
          "oLanguage": {"sEmptyTable": "No test run was found in this plan."},
          "bServerSide": true,
          "sAjaxSource": url,
          "iDisplayLength": 20,
          "sPaginationType": "full_numbers",
          "fnServerParams": function(aoData) {
            let params = jQ("#run_filter").serializeArray();
            params.forEach(function(param) {
              aoData.push(param);
            });
          }
        });
      }
    }
  },
  'reactsToRunSelection': function () {
    let that = Nitrate.TestPlans.Runs;
    let selection = jQ('.run_selector:not(:checked)');
    let controller = jQ('#id_check_all_runs');
    if (selection.length === 0) {
      controller.attr('checked', true);
    } else {
      controller.attr('checked', false);
    }
    controller.trigger('change');
  },
  'reactsToAllRunSelectorChange': function (event) {
    let that = Nitrate.TestPlans.Runs;
    if (jQ(event.target).attr('checked')) {
      that.toggleRemainingRunSelection('on');
    } else {
      that.toggleRemainingRunSelection('off');
    }
  },
  'toggleRemainingRunSelection': function (status) {
    let area = jQ('#box_select_rest');
    if (area.length) {
      if (status === 'off') {
        area.find('input:checkbox').attr('checked', false);
        area.hide();
      } else {
        area.find('input:checkbox').attr('checked', true);
        area.show();
      }
    }
  },
  'filter': function (data) {
    let queryString = jQ("#run_filter").serialize();
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
