// Create a dictionary to avoid polluting the global namespace:
var Nitrate = window.Nitrate || {}; // Ironically, this global name is not respected. So u r on ur own.
window.Nitrate = Nitrate;

Nitrate.Utils = {};
var SHORT_STRING_LENGTH = 100;
var nil;

/*
    Utility function.
    Set up a function callback for after the page has loaded
 */
Nitrate.Utils.after_page_load = function(callback) {
  jQ(window).bind('load', callback);
};

Nitrate.Utils.enableShiftSelectOnCheckbox = function (className) {
  jQ('.' + className).shiftcheckbox();
};

Nitrate.Utils.convert = function(argument, data) {
  switch (argument) {
    case 'obj_to_list':
      if (data.length !== 0 && !data.length) {
        return jQ.extend({}, {0: data, length: 1});
      }
      return data;
  }
};

/*
 * Collect form data from input elements.
 * @param {HTMLForm} f - A HTML form from where to collect data.
 */
Nitrate.Utils.formSerialize = function(f) {
  let params = {};
  jQ(f).serializeArray().forEach(function(param) {
    if (params[param.name]) {
      if (!jQ.isArray(params[param.name])) {
        params[param.name] = [params[param.name]];
      }
      params[param.name].push(param.value);
    } else {
      params[param.name] = param.value;
    }
  });
  return params;
};

jQ(window).bind('load', function(e) {
  // Initial the drop menu
  jQ('.nav_li').hover(
    function() { jQ(this).children(':eq(1)').show(); },
    function() { jQ(this).children(':eq(1)').hide(); }
  );

  // Observe the bookmark form
  if (jQ('#id_bookmark_iform').length) {
    jQ('#id_bookmark_iform').bind('submit', function(e) {
      e.stopPropagation();
      e.preventDefault();
      var url = this.action;
      var dialog = showDialog();
      var parameters = Nitrate.Utils.formSerialize(this);
      parameters.url = window.location.href;

      if (!parameters.name) {
        parameters.name = document.title;
      }

      var complete = function(t) {
        var c = function(t) {
          var returnobj = jQ.parseJSON(t.responseText);

          if (returnobj.rc !== 0) {
            window.alert(returnobj.response);
            return returnobj;
          }

          clearDialog();
          window.alert(default_messages.alert.bookmark_added);
          return returnobj;
        };

        var form_observe = function(e) {
          e.stopPropagation();
          e.preventDefault();

          addBookmark(this.action, this.method, Nitrate.Utils.formSerialize(this), c);
        };

        var form = constructForm(t.responseText, url, form_observe);
        jQ(dialog).html(form);
      };

      jQ.ajax({
        'url': url,
        'type': this.method,
        'data': parameters,
        'success': function (data, textStatus, jqXHR) {
          jQ(dialog).html(data);
        },
        'error': function (jqXHR, textStatus, errorThrown) {
          html_failure();
        },
        'complete': function(jqXHR, textStatus) {
          complete(jqXHR);
        }
      });
    });
  }
});

var default_messages = {
  'alert': {
    'no_case_selected': 'No cases selected! Please select at least one case.',
    'no_category_selected': 'No category selected! Please select a category firstly.',
    'ajax_failure': 'Communication with server got some unknown errors.',
    'tree_reloaded': 'The tree has been reloaded.',
    'last_case_run': 'It is the last case run',
    'bookmark_added': 'Bookmark added.',
    'no_run_selected': 'No run selected.',
    'no_plan_specified': 'Please specify one plan at least.'
  },
  'confirm': {
    'change_case_status': 'Are you sure you want to change the status?',
    'change_case_priority': 'Are you sure you want to change the priority?',
    'remove_case_component': 'Are you sure you want to delete these component(s)?\nYou cannot undo.',
    'remove_bookmark': 'Are you sure you wish to delete these bookmarks?',
    'remove_comment': 'Are you sure to delete the comment?',
    'remove_tag': 'Are you sure you wish to delete the tag(s)'
  },
  'link': {
    'hide_filter': 'Hide filter options',
    'show_filter': 'Show filter options',
  },
  'prompt': { 'edit_tag': 'Please type your new tag' },
  'report': {
    'hide_search': 'Hide the coverage search',
    'show_search': 'Show the coverage search'
  },
  'search': {
    'hide_filter': 'Hide Case Information Option',
    'show_filter': 'Show Case Information Option',
  }
};


/*
 * http namespace and modules
 */
(function() {
  var http = Nitrate.http || {};

  http.URLConf = {
    _mapping: {
      login: '/accounts/login/',
      logout: '/accounts/logout/',

      change_user_group: '/management/account/$id/changegroup/',
      change_user_status: '/management/account/$id/changestatus/',
      search_users: '/management/accounts/search/',

      get_form: '/ajax/form/',
      get_product_info: '/management/getinfo/',
      upload_file: '/management/uploadfile/',

      modify_plan : '/plan/$id/modify/',
      plan_assign_case: '/plan/$id/assigncase/apply/',
      plan_components : '/plans/component/',
      plan_tree_view: '/plan/$id/treeview/',
      plans: '/plans/',

      case_change_status: '/cases/changestatus/',
      case_details: '/case/$id/',
      case_plan: '/case/$id/plan/',
      cases_automated: '/cases/automated/',
      cases_category: '/cases/category/',
      cases_component: '/cases/component/',
      cases_tag: '/cases/tag/',
      change_case_order: '/case/$id/changecaseorder/',
      change_case_run_order: '/run/$id/changecaserunorder/',
      change_case_run_status: '/run/$id/execute/changestatus/',
      create_case: '/case/create/',
      modify_case: '/case/$id/modify/',
      search_case: '/cases/',

      manage_env_categories: '/management/environments/categories/',
      manage_env_properties: '/management/environments/properties/',
      manage_env_property_values: '/management/environments/propertyvalues/',
      runs_env_value: '/runs/env_value/'
    },

    reverse: function(options) {
      var name = options.name;
      if (name === undefined) {
        return undefined;
      }
      var arguments = options.arguments || {};
      var urlpattern = this._mapping[name];
      if (urlpattern === undefined) {
          return undefined;
      }
      var url = urlpattern;
      for (var key in arguments) {
          url = url.replace('$' + key, arguments[key].toString());
      }
      return url;
    }
  };

  Nitrate.http = http;
}());


// Exceptions for Ajax
function json_failure(jqXHR) {
  let responseJSON = jQ.parseJSON(jqXHR.responseText);
  // response property will be deprecated from server response.
  if (responseJSON.response) {
    window.alert(responseJSON.response);
  } else if (responseJSON.messages) {
    window.alert(responseJSON.messages);
  } else {
    window.alert(responseJSON);
  }
  return false;
}

function html_failure() {
  window.alert(default_messages.alert.ajax_failure);
  return false;
}

function json_success_refresh_page(t) {
  let returnobj = jQ.parseJSON(t.responseText);

  if (parseInt(returnobj.rc) === 0) {
    window.location.reload();
  } else {
    window.alert(returnobj.response);
    return false;
  }
}

function addBookmark(url, method, parameters, callback) {
  parameters.a = 'add';

  jQ.ajax({
    'url': url,
    'type': method,
    'data': parameters,
    'success': function (data, textStatus, jqXHR) {
      callback(jqXHR);
    },
    'error': function (jqXHR, textStatus, errorThrown) {
      json_failure(jqXHR);
    }
  });
}

function setCookie(name, value, expires, path, domain, secure) {
  document.cookie = name + "=" + escape(value) +
    ((expires) ? "; expires=" + expires.toGMTString() : "") +
    ((path) ? "; path=" + path : "") +
    ((domain) ? "; domain=" + domain : "") +
    ((secure) ? "; secure" : "");
}

function checkCookie() {
  var exp = new Date();
  exp.setTime(exp.getTime() + 1800000);
  // first write a test cookie
  setCookie("cookies", "cookies", exp, false, false, false);
  if (document.cookie.indexOf('cookies') !== -1) {
    // now delete the test cookie
    exp = new Date();
    exp.setTime(exp.getTime() - 1800000);
    setCookie("cookies", "cookies", exp, false, false, false);

    return true;
  } else {
    return false;
  }
}

function removeItem(item, tc_estimated_time) {
  var tr_estimated_time = jQ('#estimated_time').data('time');
  var remain_estimated_time = tr_estimated_time - tc_estimated_time;
  var second_value = remain_estimated_time % 60;
  var minute = parseInt(remain_estimated_time / 60);
  var minute_value = minute % 60;
  var hour = parseInt(minute / 60);
  var hour_value = hour % 24;
  var day_value = parseInt(hour / 24);

  var remain_estimated_time_value = day_value ? day_value + 'd' : '';
  remain_estimated_time_value += hour_value ? hour_value + 'h' : '';
  remain_estimated_time_value += minute_value ? minute_value + 'm' : '';
  remain_estimated_time_value += second_value ? second_value + 's' : '';

  if (!remain_estimated_time_value.length) {
    remain_estimated_time_value = '0m';
  }

  jQ('#estimated_time').data('time', remain_estimated_time);
  // TODO: can't set value through jquery setAttribute.
  document.getElementById('id_estimated_time').value = remain_estimated_time_value;
  jQ('#' + item).remove();
}

function splitString(str, num) {
  let cut_for_dot = num - 3;

  if (str.length > num) {
    return str.substring(0, cut_for_dot) + "...";
  }

  return str;
}

/*
    Set up the <option> children of the given <select> element.
    Preserving the existing selection (if any).

    @elemSelect: an HTMLSelectElement.
    @values: a list of (id, name) pairs.
    @addBlankOption: boolean. If true, prepend a "blank" option.
*/
function set_up_choices(elemSelect, values, addBlankOption) {
  // Convert HTMLOptionsCollection to Array in order to handle it conveniently later.
  var elemOptions = [];
  for (var i=0; i < elemSelect.options.length; i++) {
    elemOptions.push(elemSelect.options.item(i));
  }

  elemOptions.forEach(function (item) {
    item.remove();
  });

  var selectedIds = null;

  if (!elemSelect.multiple) {
    // Process the single select box
    selectedIds = [parseInt(elemSelect.value)];
  } else {
    // Process the select box with multiple attribute
    selectedIds = elemOptions.filter(function (item) {
      if (item.selected) {
        return parseInt(item.value);
      }
    });
  }

  var newElemOption = null;

  if (addBlankOption) {
    newElemOption = document.createElement('option');
    newElemOption.value = '';
    newElemOption.text = '---------';
    elemSelect.add(newElemOption);
  }

  values.forEach(function (item) {
    var optionValue = item[0];
    var optionText = item[1];

    newElemOption = document.createElement('option');
    newElemOption.value = optionValue;

    if (optionText.length > SHORT_STRING_LENGTH) {
      newElemOption.title = optionText;
      newElemOption.text = splitString(optionText, SHORT_STRING_LENGTH);
    } else {
      newElemOption.text = optionText;
    }

    selectedIds.forEach(function (id) {
      if (id === parseInt(optionValue)) {
        newElemOption.selected = true;
      }
    });

    elemSelect.add(newElemOption);
  });
}

function getBuildsByProductId(allow_blank, product_field, build_field) {
  if (!product_field) {
    product_field = jQ('#id_product')[0];
  }

  if (!build_field) {
    if (jQ('#id_build').length) {
      build_field = jQ('#id_build')[0];
    } else {
      window.alert('Build field does not exist');
      return false;
    }
  }

  let product_id = jQ(product_field).val();
  let no_product_is_selected = product_id === '' || product_id === null;
  if (no_product_is_selected) {
    jQ(build_field).html('<option value="">---------</option>');
    return false;
  }

  let is_active = '';
  if (jQ('#value_sub_module').length) {
    if (jQ('#value_sub_module').val() === "new_run") {
      is_active = true;
    }
  }

  if (is_active) {
    is_active = true;
  }

  jQ.ajax({
    'url': Nitrate.http.URLConf.reverse({ name: 'get_product_info' }),
    'type': 'GET',
    'data': {'info_type': 'builds', 'product_id': product_id, 'is_active': is_active},
    'success': function (data, textStatus, jqXHR) {
      let returnobj = jQ.parseJSON(jqXHR.responseText);

      set_up_choices(
        build_field,
        returnobj.map(function(o) { return [o.pk, o.fields.name]; }),
        allow_blank
      );

      if (jQ('#value_sub_module').length && jQ('#value_sub_module').val() === 'new_run') {
        if(jQ(build_field).html() === '') {
          window.alert('You should create new build first before create new run');
        }
      }
    },
    'error': function (jqXHR, textStatus, errorThrown) {
      if (jqXHR.readyState !== 0 && errorThrown !== "") {
        window.alert("Update builds and envs failed");
      }
    }
  });
}

function getEnvsByProductId(allow_blank, product_field) {
  if (!product_field) {
    product_field = jQ('#id_product')[0];
  }

  let product_id = jQ(product_field).val();
  let args = false;
  if (jQ('#value_sub_module').length) {
    if (jQ('#value_sub_module').val() === 'new_run') {
      args = 'is_active';
    }
  }

  if(product_id === '') {
    jQ('#id_env_id').html('<option value="">---------</option>');
    return true;
  }

  new Ajax.Request(
    Nitrate.http.URLConf.reverse({ name: 'get_product_info' }),
    {
      method:'get',
      parameters: {
        info_type: 'envs',
        product_id: product_id,
        args: args,
      },
      requestHeaders: {Accept: 'application/json'
    },
    onSuccess: function(t) {
      let returnobj = jQ.parseJSON(t.responseText);

      set_up_choices(
        jQ('#id_env_id')[0],
        returnobj.map(function(o) {
          return [o.pk, o.fields.name];
        }),
        allow_blank
      );

      if (document.title === "Create new test run") {
        if (jQ('#id_env_id').html() === '') {
          window.alert('You should create new enviroment first before create new run');
        }
      }
    },
    onFailure: function(jqXHR, textStatus, errorThrown) {
      if (jqXHR.readyState !== 0 && errorThrown !== "") {
        alert("Update builds and envs failed");
      }
    }
  });
}

function getVersionsByProductId(allow_blank, product_field, version_field) {
  // FIXME: why not use the passed-in value?
  product_field = jQ('#id_product')[0];

  if (!version_field) {
    if (jQ('#id_product_version').length) {
      version_field = jQ('#id_product_version')[0];
    } else {
      window.alert('Version field does not exist');
      return false;
    }
  }

  let product_id = jQ(product_field).val();

  if (!product_id && allow_blank) {
    jQ(version_field).html('<option value="">---------</option>');
      return true;
  }

  jQ.ajax({
    'url': Nitrate.http.URLConf.reverse({ name: 'get_product_info' }),
    'type': 'GET',
    'data': {'info_type': 'versions', 'product_id': product_id},
    'success': function (data, textStatus, jqXHR) {
      set_up_choices(
        version_field,
        jQ.parseJSON(jqXHR.responseText).map(function(o) {
          return [o.pk, o.fields.value];
        }),
        allow_blank
      );
    },
    'error': function (jqXHR, textStatus, errorThrown) {
      if (jqXHR.readyState !== 0 && errorThrown !== "") {
        window.alert("Update versions failed");
      }
    }
  });
}

function getComponentsByProductId(allow_blank, product_field, component_field, callback, parameters) {
  if (!parameters) {
    parameters = {};
  }

  parameters.info_type = 'components';

  // Initial the product get from
  if (!parameters || !parameters.product_id) {
    if (!product_field) {
      product_field = jQ('#id_product')[0];
    }
    parameters.product_id = jQ(product_field).val();
  }

  if (!component_field) {
    if (jQ('#id_component').length) {
      component_field = jQ('#id_component')[0];
    } else {
      window.alert('Component field does not exist');
      return false;
    }
  }

  if (parameters.product_id === '') {
    jQ(component_field).html('<option value="">---------</option>');
    return true;
  }

  jQ.ajax({
    'url': Nitrate.http.URLConf.reverse({ name: 'get_product_info' }),
    'type': 'GET',
    'data': parameters,
    'success': function (data, textStatus, jqXHR) {
      set_up_choices(
        component_field,
        jQ.parseJSON(jqXHR.responseText).map(function(o) {
          return [o.pk, o.fields.name];
        }),
        allow_blank
      );

      if (typeof callback === 'function') {
        callback.call();
      }
    },
    'error': function (jqXHR, textStatus, errorThrown) {
      if (jqXHR.readyState !== 0 && errorThrown !== "") {
        window.alert("Update components failed");
      }
    }
  });
}

/**
 * Refresh categories related to a product and fill in a SELECT element.
 * @param {boolean} allow_blank - whether to add a special option item to SELECT as a blank selected option.
 * @param product_field - the SELECT element.
 * @param category_field - the category element to fill in.
 */
function getCategoriesByProductId(allow_blank, product_field, category_field) {
  if (!product_field) {
    product_field = jQ('#id_product')[0];
  }

  if (!category_field) {
    if (jQ('#id_category').length) {
      category_field = jQ('#id_category')[0];
    } else {
      window.alert('Category field does not exist');
      return false;
    }
  }

  if (jQ(product_field).val() === '') {
    jQ(category_field).html('<option value="">---------</option>');
    return true;
  }

  jQ.ajax({
    'url': Nitrate.http.URLConf.reverse({ name: 'get_product_info' }),
    'type': 'GET',
    'data': {'info_type': 'categories', 'product_id': product_field.selectedOptions[0].value},
    'success': function (data, textStatus, jqXHR) {
      set_up_choices(
        category_field,
        jQ.parseJSON(jqXHR.responseText).map(function(o) {
          return [o.pk, o.fields.name];
        }),
        allow_blank
      );
    },
    'error': function (jqXHR, textStatus, errorThrown) {
      if (jqXHR.readyState !== 0 && errorThrown !== "") {
        alert("Update category failed");
      }
    }
  });
}

function checkProductField(product_field) {
  if (product_field) {
    return product_field;
  }

  if (jQ('#id_product').length) {
    return jQ('#id_product')[0];
  }

  return false;
}

function bind_build_selector_to_product(allow_blank, product_field, build_field) {
  product_field = checkProductField(product_field);

  if (product_field) {
    jQ(product_field).bind('change', function() {
      getBuildsByProductId(allow_blank, product_field, build_field);
    });

    getBuildsByProductId(allow_blank, product_field, build_field);
  }
}

function bind_env_selector_to_product(allow_blank) {
  jQ('#id_product_id').bind('change', function() { getEnvsByProductId(allow_blank); });
  getEnvsByProductId(allow_blank);
}

function bind_version_selector_to_product(allow_blank, load, product_field, version_field) {
  product_field = checkProductField(product_field);

  if (product_field) {
    jQ(product_field).bind('change', function() {
      getVersionsByProductId(allow_blank, product_field, version_field);
    });
    if (load) {
      getVersionsByProductId(allow_blank, product_field, version_field);
    }
  }
}

function bind_category_selector_to_product(allow_blank, load, product_field, category_field) {
  product_field = checkProductField(product_field);

  if (product_field) {
    jQ(product_field).bind('change', function() {
      getCategoriesByProductId(allow_blank, product_field, category_field);
    });
    if (load) {
      getCategoriesByProductId(allow_blank);
    }
  }
}

function bind_component_selector_to_product(allow_blank, load, product_field, component_field) {
  product_field = checkProductField(product_field);

  if (product_field) {
    jQ(product_field).bind('change', function() {
      getComponentsByProductId(allow_blank, product_field, component_field);
    });

    if (load) {
      getComponentsByProductId(allow_blank);
    }
  }
}

// Stolen from http://www.webdeveloper.com/forum/showthread.php?t=161317
function fireEvent(obj,evt) {
  var fireOnThis = obj;
  if (document.createEvent) {
    var evObj = document.createEvent('MouseEvents');
    evObj.initEvent( evt, true, false );
    fireOnThis.dispatchEvent(evObj);
  } else if(document.createEventObject) {
    fireOnThis.fireEvent('on'+evt);
  }
}

// Stolen from http://stackoverflow.com/questions/133925/javascript-post-request-like-a-form-submit
function postToURL(path, params, method) {
  method = method || "post"; // Set method to post by default, if not specified.

  // The rest of this code assumes you are not using a library.
  // It can be made less wordy if you use one.
  var form = document.createElement("form");
  form.setAttribute("method", method);
  form.setAttribute("action", path);

  let hiddenField = null;

  for(var key in params) {
    if (typeof params[key] === 'object') {
      for (var i in params[key]) {
        if (typeof params[key][i] !== 'string') {
          continue;
        }

        hiddenField = document.createElement("input");
        hiddenField.setAttribute("type", "hidden");
        hiddenField.setAttribute("name", key);
        hiddenField.setAttribute("value", params[key][i]);
        form.appendChild(hiddenField);
      }
    } else {
      hiddenField = document.createElement("input");
      hiddenField.setAttribute("type", "hidden");
      hiddenField.setAttribute("name", key);
      hiddenField.setAttribute("value", params[key]);
      form.appendChild(hiddenField);
    }
  }

  document.body.appendChild(form);    // Not entirely sure if this is necessary
  form.submit();
}

function constructTagZone(container, parameters) {
  jQ(container).html('<div class="ajax_loading"></div>');

  jQ.ajax({
    'url': '/management/tags/',
    'type': 'GET',
    'data': parameters,
    'success': function (data, textStatus, jqXHR) {
      jQ(container).html(data);
    },
    'complete': function () {
      jQ('#id_tags').autocomplete({
        'source': function(request, response) {
          jQ.ajax({
            'url': Nitrate.http.URLConf.reverse({ name: 'get_product_info' }),
            'data': {
              'name__startswith': request.term,
              'info_type': 'tags',
              'format': 'ulli',
              'field': 'name'
            },
            'success': function(data) {
              let processedData = [];
              if (data.indexOf('<li>') > -1) {
                processedData = data.slice(data.indexOf('<li>') + 4, data.lastIndexOf('</li>'))
                  .split('<li>').join('').split('</li>');
              }
              response(processedData);
            }
          });
        },
        'minLength': 2,
        'appendTo': '#id_tags_autocomplete'
      });

      jQ('#id_tag_form').bind('submit', function(e) {
        e.stopPropagation();
        e.preventDefault();

        constructTagZone(container, Nitrate.Utils.formSerialize(this));
      });

      jQ('#tag_count').text(jQ('tbody#tag').attr('count'));
    }
  });
}


function addTag(container) {
  let tag_name = jQ('#id_tags').attr('value');
  if (!tag_name.length) {
    jQ('#id_tags').focus();
  } else {
    constructTagZone(container, Nitrate.Utils.formSerialize(jQ('#id_tag_form')[0]));
  }
}

function removeTag(container, tag) {
  jQ('#id_tag_form').parent().find('input[name="a"]')[0].value = 'remove';

  let parameters = Nitrate.Utils.formSerialize(jQ('#id_tag_form')[0]);
  parameters.tags = tag;

  constructTagZone(container, parameters);
}

function editTag(container, tag) {
  let nt = prompt(default_messages.prompt.edit_tag, tag);
  if (!nt) {
    return false;
  }

  let parameters = Nitrate.Utils.formSerialize(jQ('#id_tag_form')[0]);
  parameters.tags = nt;

  jQ.ajax({
    'url': '/management/tags/',
    'type': 'GET',
    'data': parameters,
    'success': function (data, textStatus, jqXHR) {
      jQ(container).html(data);
    },
    'complete': function () {
      removeTag(container, tag);
    }
  });
}

function addBatchTag(parameters, callback, format) {
  parameters.a = 'add';
  parameters.t = 'json';
  parameters.f = format;
  batchProcessTag(parameters, callback, format);
}

function removeBatchTag(parameters, callback, format) {
  parameters.a = 'remove';
  parameters.t = 'json';
  parameters.f = format;
  batchProcessTag(parameters, callback, format);
}

function batchProcessTag(parameters, callback, format) {
  jQ.ajax({
    'url': '/management/tags/',
    'type': 'GET',
    'data': parameters,
    'traditional': true,
    'success': function (data, textStatus, jqXHR) {
      if (!format) {
        let returnobj = jQ.parseJSON(jqXHR.responseText);

        if (returnobj.response === 'ok') {
          if (callback) {
            callback.call();
          }
        } else {
          window.alert(returnobj.response);
          return false;
        }
      } else {
        callback(jqXHR);
      }
    }
  });
}


function removeComment(form, callback) {
  let parameters = Nitrate.Utils.formSerialize(form);

  jQ.ajax({
    'url': form.action,
    'type': form.method,
    'data': parameters,
    'success': function (data, textStatus, jqXHR) {
      updateCommentsCount(parameters.object_pk, false);
      callback(jqXHR);
    },
    'error': function (jqXHR, textStatus, errorThrown) {
      json_failure(jqXHR);
    }
  });
}


function submitComment(container, parameters, callback) {
  jQ(container).html('<div class="ajax_loading"></div>');

  jQ.ajax({
    'url': '/comments/post/',
    'type': 'POST',
    'data': parameters,
    'success': function (data, textStatus, jqXHR) {
      jQ(container).html(data);
    },
    'complete': function () {
      updateCommentsCount(parameters.case_id, true);
      if (callback) {
        callback();
      }
    }
  });
}

function updateCommentsCount(caseId, increase) {
  let commentDiv = jQ("#" + caseId + "_case_comment_count");
  let countText = jQ("#" + caseId + "_comments_count");
  if (increase) {
    if (commentDiv.children().length === 1) {
      commentDiv.prepend("<img src=\"/static/images/comment.png\" style=\"vertical-align: middle;\">");
    }
    countText.text(" " + (parseInt(countText.text()) + 1));
  } else {
    if (parseInt(countText.text(), 10) === 1) {
      commentDiv.html("<span id=\""+caseId+"_comments_count\"> 0</span>");
    } else {
      countText.text(" " + (parseInt(commentDiv.text()) - 1));
    }
  }
}

function previewPlan(parameters, action, callback, notice, s, c) {
  let dialog = getDialog();

  clearDialog();
  jQ(dialog).show();

  parameters.t = 'html';
  parameters.f = 'preview';

  jQ.ajax({
    'url': '/plans/',
    'type': 'GET',
    'data': parameters,
    'success': function (data, textStatus, jqXHR) {
      try {
        notice = "";
      } catch (e) {
        // do nothing
      }
      let form = constructForm(jqXHR.responseText, action, callback, notice, s, c);
      jQ(dialog).html(form);
    },
    'error': function (jqXHR, textStatus, errorThrown) {
      html_failure();
    }
  });
}

function getInfo(parameters, callback, container, allow_blank, format) {
  if (format) {
    parameters.format = format;
  }

  jQ.ajax({
    'url': Nitrate.http.URLConf.reverse({ name: 'get_product_info' }),
    'type': 'GET',
    'data': parameters,
    'success': function (data, textStatus, jqXHR) {
      if (callback) {
        callback(jqXHR, allow_blank, container);
      }
    },
    'error': function (jqXHR, textStatus, errorThrown) {
      window.alert("Get info " + parameters.info_type + " failed");
      return false;
    }
  });
}

function getForm(container, app_form, parameters, callback, format) {
  if (!parameters) {
    parameters = {};
  }

  parameters.app_form = app_form;
  parameters.format = format;

  jQ.ajax({
    'url': Nitrate.http.URLConf.reverse({ name: 'get_form'}),
    'type': 'GET',
    'data': parameters,
    'success': function (data, textStatus, jqXHR) {
      jQ(container).html(data);
      callback(jqXHR);
    },
    'error': function (jqXHR, textStatus, errorThrown) {
      window.alert('Getting form get errors');
      return false;
    }
  });
}

function updateRunStatus(content_type, object_pk, field, value, value_type, callback) {
  if (!value_type) {
    value_type = 'str';
  }

  if (typeof object_pk === 'object') {
    object_pk = object_pk.join(',');
  }
  jQ.ajax({
    'url': '/ajax/update/case-run-status',
    'type': 'POST',
    'data': {
      'content_type': content_type,
      'object_pk': object_pk,
      'field': field,
      'value': value,
      'value_type': value_type
    },
    'success': function (data, textStatus, jqXHR) {
      callback();
    },
    'error': function (jqXHR, textStatus, errorThrown) {
      json_failure(jqXHR);
    }
  });
}

function updateObject(content_type, object_pk, field, value, value_type, callback) {
  if (!value_type) {
    value_type = 'str';
  }

  if (typeof object_pk === 'object') {
    object_pk = object_pk.join(',');
  }

  jQ.ajax({
    'url': '/ajax/update/',
    'type': 'POST',
    'data': {
      'content_type': content_type,
      'object_pk': object_pk,
      'field': field,
      'value': value,
      'value_type': value_type
    },
    'success': function (data, textStatus, jqXHR) {
      callback(jqXHR);
    },
    'error': function (jqXHR, textStatus, errorThrown) {
      json_failure(jqXHR);
    }
  });
}

function reloadWindow(jqXHR) {
  let returnobj = jQ.parseJSON(jqXHR.responseText);
  if (returnobj.rc !== 0) {
    window.alert(returnobj.response);
    return false;
  }
  window.location.reload();
}

/**
 * Get info and update specific objects
 * @param {object} parameters - Use for getInfo method
 * @param {string} content_type - use for updateObject method
 * @param object_pks - Int/Array - use for updateObject method
 * @param {string} field - use for updateObject method
 * @param {function} callback - use for updateObject method
 */
function getInfoAndUpdateObject(parameters, content_type, object_pks, field, callback) {
  getInfo(parameters, function (jqXHR) {
    let returnobj = jQ.parseJSON(jqXHR.responseText);

    // FIXME: Display multiple items and let user to select one
    if (returnobj.length === 0) {
      window.alert('Nothing found in database');
      return false;
    }

    if (returnobj.length > 1) {
      window.alert('Multiple instances reached, please define the condition more clear.');
      return false;
    }

    updateObject(content_type, object_pks, field, returnobj[0].pk, 'str', callback || reloadWindow);
  });
}

function getDialog(element) {
  if (!element) {
    return jQ('#dialog')[0];
  }
  return element;
}

function showDialog(element) {
  return jQ(getDialog(element)).show()[0];
};

function clearDialog(element) {
  let dialog = getDialog(element);

  jQ(dialog).html(getAjaxLoading());
  return jQ(dialog).hide()[0];
};

function getAjaxLoading(id) {
  let e = jQ('<div>', {'class': 'ajax_loading'})[0];
  if (id) {
    e.id = id;
  }

  return e;
}

function clickedSelectAll(checkbox, form, name) {
  let checkboxes = jQ(form).parent().find('input[name='+ name + ']');
  for (let i = 0; i < checkboxes.length; i++) {
    checkboxes[i].checked = checkbox.checked? true:false;
  }
}

function bindSelectAllCheckbox(element, form, name) {
  jQ(element).bind('click', function(e) {
    clickedSelectAll(this, form, name);
  });
}

function constructForm(content, action, form_observe, info, s, c) {
  let f = jQ('<form>', {'action': action});
  let i = jQ('<div>', {'class': 'alert'});
  if (info) {
    i.html(info);
  }

  if (!s) {
    s = jQ('<input>', {'type': 'submit', 'value': 'Submit'});
  }

  if (!c) {
    c = jQ('<input>', {'type': 'button', 'value': 'Cancel'});
    c.bind('click', function(e) {
      clearDialog();
    });
  }

  if (form_observe) {
    f.bind('submit', form_observe);
  }

  f.html(content);
  f.append(i);
  f.append(s);
  f.append(c);

  return f[0];
}

// Enhanced from showAddAnotherPopup in RelatedObjectLookups.js for Admin
function popupAddAnotherWindow(triggeringLink, parameters) {
  let name = triggeringLink.id.replace(/^add_/, '');
  name = id_to_windowname(name);
  let href = triggeringLink.href;
  if (href.indexOf('?') === -1) {
    href += '?_popup=1';
  } else {
    href += '&_popup=1';
  }

  // IMPOROMENT: Add parameters.
  // FIXME: Add multiple parameters here
  if (parameters) {
    href += '&' + parameters + '=' + jQ('#id_' + parameters).val();
  }

  let win = window.open(href, name, 'height=500,width=800,resizable=yes,scrollbars=yes');
  win.focus();
  return false;
}

function exportCase(url, form, table) {
  var selection = serializeCaseFromInputList2(table);
  var emptySelection = !selection.selectAll & selection.selectedCasesIds.length === 0;
  if (emptySelection) {
    window.alert(default_messages.alert.no_case_selected);
    return false;
  }

  var params = serialzeCaseForm(form, table, true);
  if (selection.selectAll) {
    params.selectAll = selection.selectAll;
  }
  // replace with selected cases' IDs
  params.case = selection.selectedCasesIds;
  postToURL(url, params);
}

var printableCases = exportCase;
