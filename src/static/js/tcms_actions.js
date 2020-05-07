// Create a dictionary to avoid polluting the global namespace:
const Nitrate = window.Nitrate || {}; // Ironically, this global name is not respected. So u r on ur own.
window.Nitrate = Nitrate;

Nitrate.Utils = {};
const SHORT_STRING_LENGTH = 100;

/*
    Utility function.
    Set up a function callback for after the page has loaded
 */
Nitrate.Utils.after_page_load = function(callback) {
  jQ(window).on('load', callback);
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

/**
 * Collect form data from input elements.
 * @param {HTMLFormElement} f - A HTML form from where to collect data.
 * @returns {Object} a mapping containing form data.
 */
Nitrate.Utils.formSerialize = function(f) {
  let data = {};
  jQ(f).serializeArray().forEach(function (field) {
    let name = field.name;
    let existingValue = data[field.name];
    if (existingValue === undefined) {
      data[name] = field.value;
    } else {
      if (!jQ.isArray(existingValue)) {
        data[name] = [existingValue];
      }
      data[name].push(field.value);
    }
  });
  return data;
};

/**
 * Simple wrapper of jQuery.ajax to add header for CSRF.
 * @param {string} url
 * @param {object} options
 */
function $ajax(url, options) {
  options = Object.assign({}, options, {
    beforeSend: function (xhr, settings) {
      if (!/^(GET|HEAD|OPTIONS|TRACE)$/.test(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", globalCsrfToken);
      }
    },
  });
  jQ.ajax(url, options);
}

/**
 * Send a AJAX request to the backend server and handle the response. The response from backend is
 * expected to be in JSON data format.
 * @param {object} options - configure the jQuery.ajax call.
 * @param {string} options.url - url of the resource.
 * @param {string} [options.method] - type of the request. Default is POST.
 * @param {object} [options.data] - request data.
 * @param {boolean} [options.traditional] - whether to use the traditional style of param
 *                                          serialization. Refer to traditional argument of
 *                                          jQuery.ajax.
 * @param {boolean} [options.sync] - send the request in a synchronous way.
 * @param {string} [options.forbiddenMessage] - alternative message shown when server responses 403.
 * @param {string} [options.badRequestMessage] - alternative message shown when server responses 400.
 * @param {string} [options.errorMessage] - alternative message shown when server responses
 *                                          unsuccessfully like 500 and 400. If omitted, default
 *                                          message will be shown for each specific response,
 *                                          please refer to the code.
 * @param {function} [options.success] - hook to success option of jQuery.ajax. If omitted, a
 *                                       default callback will be hooked to reload the page.
 */
function sendAjaxRequest(options) {
  $ajax(options.url, {
    type: options.method || 'post',
    dataType: 'json',
    data: options.data,
    async: !options.sync,
    traditional: options.traditional,
    success: options.success || function() { window.location.reload(); },
    statusCode: {
      500: function () {
        if (options.errorMessage !== undefined) {
          window.alert(options.errorMessage);
          return;
        }
        window.alert(
          'Something wrong in the server. ' +
          'Please contact administrator to deal with this issue.'
        );
      },
      // How about 404?
      //
      400: function (xhr) {
        if (options.errorMessage !== undefined) {
          window.alert(options.errorMessage);
          return;
        }
        if (options.badRequestMessage !== undefined) {
          window.alert(options.badRequestMessage);
          return;
        }

        let data = JSON.parse(xhr.responseText);
        // response property will be deprecated from server response.
        // TODO: after the AJAX response is unified, just use the responseJSON.message.
        let msg = data.message || data.response || data.messages || data;
        if (Array.isArray(msg)) {
          window.alert(msg.join('\n'));
        } else {
          window.alert(msg);
        }
      },
      403: function () {
        window.alert(
          options.forbiddenMessage || 'You are not allowed to perform this operation.'
        );
      }
    }
  });
}

/**
 * Wrapper of sendAjaxRequest to send an HTTP GET request.
 * @param {object} options
 */
function getRequest(options) {
  let forwardOptions = Object.assign({}, options, {'method': 'GET'})
  return sendAjaxRequest(forwardOptions);
}

/**
 * Wrapper of sendAjaxRequest to send an HTTP POST request.
 * @param {object} options
 */
function postRequest(options) {
  let forwardOptions = Object.assign({}, options, {'method': 'POST'})
  return sendAjaxRequest(forwardOptions);
}

/**
 * Send request and expect server responses content in HTML.
 * @param {object} options - configure the jQuery.ajax call.
 * @param {string} options.url - url of the resource.
 * @param {string} [options.method] - type of the request. Default is GET.
 * @param {object} [options.data] - request data.
 * @param {boolean} [options.traditional] - whether to use the traditional style of param
 *                                          serialization. Refer to traditional argument of
 *                                          jQuery.ajax.
 * @param {string} [options.forbiddenMessage] - alternative message shown when server responses 403.
 * @param {string} [options.badRequestMessage] - alternative message shown when server responses 400.
 * @param {string} [options.notFoundMessage] - alternative message shown when server responses 404.
 * @param {function} [options.success] - hook to success option of jQuery.ajax. If omitted, a
 *                                       default callback will be hooked to fill the content
 *                                       returned from server side in the specified container
 *                                       element and invoke the callback if specified.
 * @param {HTMLElement} [options.container] - an HTML container element which the content
 *                                            returned from server will be filled in.
 * @param {function} [options.callbackAfterFillIn] - a function will be called after the returned
 *                                                   content is filled in the given container.
 */
function sendHTMLRequest(options) {
  $ajax(options.url, {
    type: options.method || 'GET',
    data: options.data,
    dataType: 'html',
    traditional: options.traditional,
    success: options.success || function (data, textStatus, xhr) {
      jQ(options.container).html(data);
      if (options.callbackAfterFillIn !== undefined)
        options.callbackAfterFillIn(xhr)
    },
    statusCode: {
      404: function (xhr) {
        window.alert(
          options.notFoundMessage ||
          xhr.responseText ||
          'Requested resource is not found.'
        );
      },
      400: function (xhr) {
        window.alert(
          options.badRequestMessage ||
          xhr.responseText ||
          'The request is invalid to be processed by the server.'
        );
      },
      403: function (xhr) {
        window.alert(
          options.forbiddenMessage ||
          xhr.responseText ||
          'You are not allowed to do this operation.'
        );
      }
    }
  });
}

function postHTMLRequest(options) {
  let forwardOptions = Object.assign({}, options, {method: 'POST'});
  sendHTMLRequest(forwardOptions);
}

jQ(window).on('load', function(e) {
  // Initial the drop menu
  jQ('.nav_li').hover(
    function() { jQ(this).children(':eq(1)').show(); },
    function() { jQ(this).children(':eq(1)').hide(); }
  );

  // Observe the bookmark form
  if (jQ('#id_bookmark_iform').length) {
    jQ('#id_bookmark_iform').on('submit', function(e) {
      e.stopPropagation();
      e.preventDefault();

      let url = this.action;
      let dialog = showDialog();
      let parameters = Nitrate.Utils.formSerialize(this);
      parameters.url = window.location.href;

      if (!parameters.name) {
        parameters.name = document.title;
      }

      sendHTMLRequest({
        url: url,
        data: parameters,
        container: dialog,
        callbackAfterFillIn: function(xhr) {
          jQ(dialog).html(constructForm(xhr.responseText, url, function (e) {
            e.stopPropagation();
            e.preventDefault();

            addBookmark(this.action, this.method, Nitrate.Utils.formSerialize(this), function (responseData) {
              clearDialog();
              window.alert(default_messages.alert.bookmark_added);
              return responseData;
            });
          }));
        },
      });
    });
  }
});

const default_messages = {
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
  let http = Nitrate.http || {};

  http.URLConf = {
    _mapping: {
      login: '/accounts/login/',
      logout: '/accounts/logout/',

      change_user_group: '/management/account/$id/changegroup/',
      change_user_status: '/management/account/$id/changestatus/',
      search_users: '/management/accounts/search/',

      get_form: '/ajax/form/',
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
      if (options.name === undefined) {
        return undefined;
      }
      let urlpattern = this._mapping[options.name];
      if (urlpattern === undefined) {
          return undefined;
      }
      let url = urlpattern;
      let arguments = options.arguments || {};
      for (let key in arguments) {
          url = url.replace('$' + key, arguments[key].toString());
      }
      return url;
    }
  };

  Nitrate.http = http;
}());


// Exceptions for Ajax
// FIXME: remove this function from here eventually
function json_failure(xhr) {
  let responseJSON = jQ.parseJSON(xhr.responseText);
  // response property will be deprecated from server response.
  // TODO: after the AJAX response is unified, just use the responseJSON.message.
  let msg = responseJSON.message ||
            responseJSON.response ||
            responseJSON.messages ||
            responseJSON;
  if (Array.isArray(msg)) {
    window.alert(msg.join('\n'));
  } else {
    window.alert(msg);
  }
  return false;
}

function addBookmark(url, method, parameters, callback) {
  parameters.a = 'add';
  // FIXME: use POST
  getRequest({url: url, data: parameters, success: callback});
}

function setCookie(name, value, expires, path, domain, secure) {
  document.cookie = name + "=" + escape(value) +
    ((expires) ? "; expires=" + expires.toGMTString() : "") +
    ((path) ? "; path=" + path : "") +
    ((domain) ? "; domain=" + domain : "") +
    ((secure) ? "; secure" : "");
}

function checkCookie() {
  let exp = new Date();
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

/**
 * Remove a case from test run new page.
 * @param {string} item - the HTML id of a container element containing the case to be removed.
 * @param {number} caseEstimatedTime - the case' estimated time.
 */
function removeItem(item, caseEstimatedTime) {
  let tr_estimated_time = jQ('#estimated_time').data('time');
  let remain_estimated_time = tr_estimated_time - caseEstimatedTime;
  let second_value = remain_estimated_time % 60;
  let minute = parseInt(remain_estimated_time / 60);
  let minute_value = minute % 60;
  let hour = parseInt(minute / 60);
  let hour_value = hour % 24;
  let day_value = parseInt(hour / 24);

  let remain_estimated_time_value = day_value ? day_value + 'd' : '';
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
  if (str.length > num) {
    return str.substring(0, num - 3) + "...";
  }
  return str;
}

/**
 * Setup option of a given select element in place. The original selection is preserved.
 * @param {HTMLSelectElement} elemSelect - the select element to update the options.
 * @param {Array} values - A list of 2-tuple of options, the first is value and the other is the text.
 * @param {boolean} addBlankOption - whether to add a blank option optionally.
 */
function setUpChoices(elemSelect, values, addBlankOption) {
  let originalSelectedIds = [];
  let selectedOptions = elemSelect.selectedOptions;
  for (let i = 0; i < selectedOptions.length; i++) {
    let option = selectedOptions[i];
    if (option.selected) originalSelectedIds.push(option.value);
  }

  // Remove all options
  for (let i = elemSelect.options.length - 1; i >= 0; i--)
    elemSelect.options[i].remove();

  let newOption = null;

  if (addBlankOption) {
    newOption = document.createElement('option');
    newOption.value = '';
    newOption.text = '---------';
    elemSelect.add(newOption);
  }

  values.forEach(function (item) {
    let optionValue = item[0], optionText = item[1];

    newOption = document.createElement('option');
    newOption.value = optionValue;

    if (optionText.length > SHORT_STRING_LENGTH) {
      newOption.title = optionText;
      newOption.text = splitString(optionText, SHORT_STRING_LENGTH);
    } else {
      newOption.text = optionText;
    }

    newOption.selected = originalSelectedIds.indexOf(optionValue) > -1;
    elemSelect.add(newOption);
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

  getRequest({
    url: '/management/getinfo/',
    data: {
      'info_type': 'builds',
      'product_id': product_id,
      'is_active': is_active
    },
    errorMessage: 'Update builds failed.',
    success: function (data) {
      setUpChoices(
        build_field,
        data.map(function(o) { return [o.pk, o.fields.name]; }),
        allow_blank
      );

      if (jQ('#value_sub_module').length && jQ('#value_sub_module').val() === 'new_run') {
        if(jQ(build_field).html() === '') {
          window.alert('You should create new build first before create new run');
        }
      }
    },
  });
}

// TODO: remove this function. It is not used.
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

  getRequest({
    url: '/management/getinfo/',
    data: {info_type: 'envs', product_id: product_id, args: args},
    errorMessage: 'Update builds and envs failed',
    success: function (data) {
      setUpChoices(
        jQ('#id_env_id')[0],
        data.map(function(o) {return [o.pk, o.fields.name];}),
        allow_blank
      );

      if (document.title === "Create new test run") {
        if (jQ('#id_env_id').html() === '') {
          window.alert('You should create new enviroment first before create new run');
        }
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

  getRequest({
    url: '/management/getinfo/',
    data: {'info_type': 'versions', 'product_id': product_id},
    success: function (data) {
      setUpChoices(
        version_field,
        data.map(function(o) { return [o.pk, o.fields.value]; }),
        allow_blank
      );
    },
    errorMessage: 'Update versions failed.',
  });
}

function getComponentsByProductId(allow_blank, product_field, component_field, callback, parameters) {
  parameters = parameters || {};
  parameters.info_type = 'components';

  // Initial the product get from
  if (! parameters.product_id) {
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

  getRequest({
    url: '/management/getinfo/',
    data: parameters,
    errorMessage: 'Update components failed.',
    success: function (data) {
      setUpChoices(
        component_field,
        data.map(function(o) { return [o.pk, o.fields.name]; }),
        allow_blank
      );

      if (callback) { callback(); }
    },
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

  getRequest({
    url: '/management/getinfo/',
    data: {
      info_type: 'categories',
      product_id: product_field.selectedOptions[0].value
    },
    errorMessage: 'Update category failed.',
    success: function (data) {
      setUpChoices(
        category_field,
        data.map(function(o) {return [o.pk, o.fields.name];}),
        allow_blank
      );
    },
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
    jQ(product_field).on('change', function() {
      getBuildsByProductId(allow_blank, product_field, build_field);
    });

    getBuildsByProductId(allow_blank, product_field, build_field);
  }
}

function bind_env_selector_to_product(allow_blank) {
  jQ('#id_product_id').on('change', function() { getEnvsByProductId(allow_blank); });
  getEnvsByProductId(allow_blank);
}

function bind_version_selector_to_product(allow_blank, load, product_field, version_field) {
  product_field = checkProductField(product_field);

  if (product_field) {
    jQ(product_field).on('change', function() {
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
    jQ(product_field).on('change', function() {
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
    jQ(product_field).on('change', function() {
      getComponentsByProductId(allow_blank, product_field, component_field);
    });

    if (load) {
      getComponentsByProductId(allow_blank);
    }
  }
}

// Stolen from http://www.webdeveloper.com/forum/showthread.php?t=161317
function fireEvent(obj,evt) {
  let fireOnThis = obj;
  if (document.createEvent) {
    let evObj = document.createEvent('MouseEvents');
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
  let form = document.createElement("form");
  form.setAttribute("method", method);
  form.setAttribute("action", path);

  let hiddenField = null;

  for(let key in params) {
    if (typeof params[key] === 'object') {
      for (let i in params[key]) {
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

  let csrfTokenHidden = document.createElement('input');
  csrfTokenHidden.setAttribute('type', 'hidden');
  csrfTokenHidden.setAttribute('name', 'csrfmiddlewaretoken');
  csrfTokenHidden.setAttribute('value', globalCsrfToken);
  form.appendChild(csrfTokenHidden);

  document.body.appendChild(form);    // Not entirely sure if this is necessary
  form.submit();
}

function constructTagZone(container, parameters) {
  jQ(container).html('<div class="ajax_loading"></div>');

  sendHTMLRequest({
    url: '/management/tags/',
    data: parameters,
    container: container,
    callbackAfterFillIn: function () {
      jQ('#id_tags').autocomplete({
        'minLength': 2,
        'appendTo': '#id_tags_autocomplete',
        'source': function(request, response) {
          sendHTMLRequest({
            url: '/management/getinfo/',
            data: {
              name__startswith: request.term,
              info_type: 'tags',
              format: 'ulli',
              field: 'name'
            },
            success: function(data) {
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

      jQ('#id_tag_form').on('submit', function(e) {
        e.stopPropagation();
        e.preventDefault();

        constructTagZone(container, Nitrate.Utils.formSerialize(this));
      });

      jQ('#tag_count').text(jQ('tbody#tag').attr('count'));
    },
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

  sendHTMLRequest({
    url: '/management/tags/',
    data: parameters,
    container: container,
    callbackAfterFillIn: function () {
      removeTag(container, tag);
    }
  });
}

function addBatchTag(parameters, callback, format) {
  parameters.a = 'add';
  parameters.t = 'json';
  parameters.f = format;

  sendHTMLRequest({
    url: '/management/tags/',
    data: parameters,
    traditional: true,
    success: function (data, textStatus, xhr) { callback(xhr); },
  });
}

function removeComment(form, callback) {
  let parameters = Nitrate.Utils.formSerialize(form);

  postRequest({
    url: form.action,
    data: parameters,
    success: function (data) {
      updateCommentsCount(parameters.object_pk, false);
      callback(data);
    },
  });
}


function submitComment(container, parameters, callback) {
  // FIXME: Remove parameter container, it is not useless here.
  jQ(container).html('<div class="ajax_loading"></div>');

  postRequest({
    url: '/comments/post/',
    data: parameters,
    success: function () {
      updateCommentsCount(parameters.object_pk, true);
      if (callback) callback();
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

/**
 * Preview Plan
 * @param parameters
 * @param action
 * @param {function} callback - a function with only one event argument will be bound to a HTMLFormElement submit event.
 * @param notice
 * @param s
 * @param c
 */
function previewPlan(parameters, action, callback, notice, s, c) {
  let dialog = getDialog();
  clearDialog();
  jQ(dialog).show();

  sendHTMLRequest({
    url: '/plans/',
    data: Object.assign({}, parameters, {t: 'html', f: 'preview'}),
    success: function (data, textStatus, xhr) {
      jQ(dialog).html(
        constructForm(xhr.responseText, action, callback, notice, s, c)
      );
    },
  });
}

function getForm(container, app_form, parameters, callback, format) {
  if (!parameters) {
    parameters = {};
  }

  parameters.app_form = app_form;
  parameters.format = format;

  sendHTMLRequest({
    url: Nitrate.http.URLConf.reverse({ name: 'get_form'}),
    data: parameters,
    container: container,
    callbackAfterFillIn: callback
  });
}

/**
 * Update run status.
 * @param content_type
 * @param object_pk
 * @param field
 * @param value
 * @param value_type
 * @param {function} callback - a function will be called when AJAX request succeeds. This function
 *                              accepts only one argument of the parsed JSON data returned from
 *                              server side.
 */
function updateRunStatus(content_type, object_pk, field, value, value_type, callback) {
  postRequest({
    url: '/ajax/update/case-run-status',
    success: callback,
    data: {
      content_type: content_type,
      object_pk: Array.isArray(object_pk) ? object_pk.join(',') : object_pk,
      field: field,
      value: value,
      value_type: value_type || 'str'
    }
  });
}

/**
 * Update one object property at a time.
 * @param {string} content_type
 * @param {number} object_pk
 * @param {string} field
 * @param {string} value
 * @param {string} value_type
 * @param {function} [callback] - a function will be called when AJAX request succeeds. This
 *                                function should accept only one argument, that is the parsed JSON
 *                                data returned from server side. If omitted, it will cause
 *                                undefined is passed to postRequest, and default behavior of
 *                                reloading current page will be triggered as a result.
 */
function updateObject(content_type, object_pk, field, value, value_type, callback) {
  postRequest({
    url: '/ajax/update/',
    success: callback,
    data: {
      content_type: content_type,
      object_pk: Array.isArray(object_pk) ? object_pk.join(',') : object_pk,
      field: field,
      value: value,
      value_type: value_type || 'str'
    }
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
}

function clearDialog(element) {
  let dialog = getDialog(element);

  jQ(dialog).html(getAjaxLoading());
  return jQ(dialog).hide()[0];
}

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
  jQ(element).on('click', function(e) {
    clickedSelectAll(this, form, name);
  });
}

/**
 * Construct an HTML form element.
 * @param content
 * @param action
 * @param {function} form_observe - an optional function bound to the generated form's submit event.
 * @param info
 * @param s
 * @param c
 * @returns the form element.
 */
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
    c.on('click', function(e) {
      clearDialog();
    });
  }

  if (form_observe) {
    f.on('submit', form_observe);
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

/**
 * Collect selected case IDs from a given container and submit them to a specific location. The
 * container element should have children HTMLInputElement with type checkbox and name case.
 * @param {string} url - the URL for exporting cases.
 * @param {HTMLElement} container - a container element from where to find out selected case IDs.
 */
function submitSelectedCaseIDs(url, container) {
  let selectedCaseIDs = getSelectedCaseIDs(container);
  if (selectedCaseIDs.length === 0) {
    window.alert(default_messages.alert.no_case_selected);
    return;
  }
  postToURL(url, {case: selectedCaseIDs});
}
