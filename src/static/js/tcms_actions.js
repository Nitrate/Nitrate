/* eslint no-redeclare: "off" */
/* eslint no-unused-vars: "off" */

// Create a dictionary to avoid polluting the global namespace:
const Nitrate = window.Nitrate || {}; // Ironically, this global name is not respected. So u r on ur own.
window.Nitrate = Nitrate;

Nitrate.Utils = {};
const SHORT_STRING_LENGTH = 100;

/*
    Utility function.
    Set up a function callback for after the page has loaded
 */
Nitrate.Utils.after_page_load = function (callback) {
  jQ(window).on('load', callback);
};

Nitrate.Utils.convert = function (argument, data) {
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
Nitrate.Utils.formSerialize = function (f) {
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
        xhr.setRequestHeader('X-CSRFToken', globalCsrfToken);
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
    success: options.success || function () { window.location.reload(); },
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
      if (options.callbackAfterFillIn !== undefined) {
        options.callbackAfterFillIn(xhr)
      }
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

jQ(window).on('load', function () {
  // Initial the drop menu
  jQ('.nav_li').hover(
    function () { jQ(this).children(':eq(1)').show(); },
    function () { jQ(this).children(':eq(1)').hide(); }
  );

  // Observe the bookmark form
  if (jQ('#id_bookmark_iform').length) {
    jQ('#id_bookmark_iform').on('submit', function (e) {
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
        callbackAfterFillIn: function (xhr) {
          jQ(dialog).html(constructForm(xhr.responseText, url, function (e) {
            e.stopPropagation();
            e.preventDefault();

            addBookmark(this.action, this.method, Nitrate.Utils.formSerialize(this), function (responseData) {
              clearDialog();
              window.alert(defaultMessages.alert.bookmark_added);
              return responseData;
            });
          }));
        },
      });
    });
  }
});

const defaultMessages = {
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
  'prompt': {'edit_tag': 'Please type your new tag'},
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
(function () {
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

    reverse: function (options) {
      if (options.name === undefined) {
        return undefined;
      }
      let urlpattern = this._mapping[options.name];
      if (urlpattern === undefined) {
        return undefined;
      }
      let url = urlpattern;
      let args = options.arguments || {};
      for (let key in args) {
        url = url.replace('$' + key, args[key].toString());
      }
      return url;
    }
  };

  Nitrate.http = http;
}());


function addBookmark(url, method, parameters, callback) {
  parameters.a = 'add';
  // FIXME: use POST
  getRequest({url: url, data: parameters, success: callback});
}

function splitString(str, num) {
  if (str.length > num) {
    return str.substring(0, num - 3) + '...';
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
    if (option.selected) {
      originalSelectedIds.push(option.value);
    }
  }

  // Remove all options
  for (let i = elemSelect.options.length - 1; i >= 0; i--) {
    elemSelect.options[i].remove();
  }

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

function getBuildsByProductId(allowBlank, productField, buildField) {
  if (!productField) {
    productField = jQ('#id_product')[0];
  }

  if (!buildField) {
    if (jQ('#id_build').length) {
      buildField = jQ('#id_build')[0];
    } else {
      window.alert('Build field does not exist');
      return false;
    }
  }

  let productId = jQ(productField).val();
  let noProductIsSelected = productId === '' || productId === null;
  if (noProductIsSelected) {
    jQ(buildField).html('<option value="">---------</option>');
    return false;
  }

  let isActive = '';
  if (jQ('#value_sub_module').length) {
    if (jQ('#value_sub_module').val() === 'new_run') {
      isActive = true;
    }
  }

  if (isActive) {
    isActive = true;
  }

  getRequest({
    url: '/management/getinfo/',
    data: {
      'info_type': 'builds',
      'product_id': productId,
      'is_active': isActive
    },
    errorMessage: 'Update builds failed.',
    success: function (data) {
      setUpChoices(
        buildField,
        data.map(function (o) { return [o.pk, o.fields.name]; }),
        allowBlank
      );

      if (jQ('#value_sub_module').length && jQ('#value_sub_module').val() === 'new_run') {
        if(jQ(buildField).html() === '') {
          window.alert('You should create new build first before create new run');
        }
      }
    },
  });
}

// TODO: remove this function. It is not used.
function getEnvsByProductId(allowBlank, productField) {
  if (!productField) {
    productField = jQ('#id_product')[0];
  }

  let productId = jQ(productField).val();
  let args = false;
  if (jQ('#value_sub_module').length) {
    if (jQ('#value_sub_module').val() === 'new_run') {
      args = 'is_active';
    }
  }

  if(productId === '') {
    jQ('#id_env_id').html('<option value="">---------</option>');
    return true;
  }

  getRequest({
    url: '/management/getinfo/',
    data: {info_type: 'envs', product_id: productId, args: args},
    errorMessage: 'Update builds and envs failed',
    success: function (data) {
      setUpChoices(
        jQ('#id_env_id')[0],
        data.map(function (o) {return [o.pk, o.fields.name];}),
        allowBlank
      );

      if (document.title === 'Create new test run') {
        if (jQ('#id_env_id').html() === '') {
          window.alert('You should create new enviroment first before create new run');
        }
      }
    }
  });
}

function getVersionsByProductId(allowBlank, productField, versionField) {
  // FIXME: why not use the passed-in value?
  productField = jQ('#id_product')[0];

  if (!versionField) {
    if (jQ('#id_product_version').length) {
      versionField = jQ('#id_product_version')[0];
    } else {
      window.alert('Version field does not exist');
      return false;
    }
  }

  let productId = jQ(productField).val();

  if (!productId && allowBlank) {
    jQ(versionField).html('<option value="">---------</option>');
    return true;
  }

  getRequest({
    url: '/management/getinfo/',
    data: {'info_type': 'versions', 'product_id': productId},
    success: function (data) {
      setUpChoices(
        versionField,
        data.map(function (o) { return [o.pk, o.fields.value]; }),
        allowBlank
      );
    },
    errorMessage: 'Update versions failed.',
  });
}

function getComponentsByProductId(allowBlank, productField, componentField, callback, parameters) {
  parameters = parameters || {};
  parameters.info_type = 'components';

  // Initial the product get from
  if (! parameters.product_id) {
    if (!productField) {
      productField = jQ('#id_product')[0];
    }
    parameters.product_id = jQ(productField).val();
  }

  if (!componentField) {
    if (jQ('#id_component').length) {
      componentField = jQ('#id_component')[0];
    } else {
      window.alert('Component field does not exist');
      return false;
    }
  }

  if (parameters.product_id === '') {
    jQ(componentField).html('<option value="">---------</option>');
    return true;
  }

  getRequest({
    url: '/management/getinfo/',
    data: parameters,
    errorMessage: 'Update components failed.',
    success: function (data) {
      setUpChoices(
        componentField,
        data.map(function (o) { return [o.pk, o.fields.name]; }),
        allowBlank
      );

      if (callback) { callback(); }
    },
  });
}

/**
 * Refresh categories related to a product and fill in a SELECT element.
 * @param {boolean} allowBlank - whether to add a special option item to SELECT as a blank selected option.
 * @param productField - the SELECT element.
 * @param categoryField - the category element to fill in.
 */
function getCategoriesByProductId(allowBlank, productField, categoryField) {
  if (!productField) {
    productField = jQ('#id_product')[0];
  }

  if (!categoryField) {
    if (jQ('#id_category').length) {
      categoryField = jQ('#id_category')[0];
    } else {
      window.alert('Category field does not exist');
      return false;
    }
  }

  if (jQ(productField).val() === '') {
    jQ(categoryField).html('<option value="">---------</option>');
    return true;
  }

  getRequest({
    url: '/management/getinfo/',
    data: {
      info_type: 'categories',
      product_id: productField.selectedOptions[0].value
    },
    errorMessage: 'Update category failed.',
    success: function (data) {
      setUpChoices(
        categoryField,
        data.map(function (o) {return [o.pk, o.fields.name];}),
        allowBlank
      );
    },
  });
}

function checkProductField(productField) {
  if (productField) {
    return productField;
  }

  if (jQ('#id_product').length) {
    return jQ('#id_product')[0];
  }

  return false;
}

function bindBuildSelectorToProduct(allowBlank, productField, buildField) {
  productField = checkProductField(productField);

  if (productField) {
    jQ(productField).on('change', function () {
      getBuildsByProductId(allowBlank, productField, buildField);
    });

    getBuildsByProductId(allowBlank, productField, buildField);
  }
}

function bindVersionSelectorToProduct(allowBlank, load, productField, versionField) {
  productField = checkProductField(productField);

  if (productField) {
    jQ(productField).on('change', function () {
      getVersionsByProductId(allowBlank, productField, versionField);
    });
    if (load) {
      getVersionsByProductId(allowBlank, productField, versionField);
    }
  }
}

function bindCategorySelectorToProduct(allowBlank, load, productField, categoryField) {
  productField = checkProductField(productField);

  if (productField) {
    jQ(productField).on('change', function () {
      getCategoriesByProductId(allowBlank, productField, categoryField);
    });
    if (load) {
      getCategoriesByProductId(allowBlank);
    }
  }
}

function bindComponentSelectorToProduct(allowBlank, load, productField, componentField) {
  productField = checkProductField(productField);

  if (productField) {
    jQ(productField).on('change', function () {
      getComponentsByProductId(allowBlank, productField, componentField);
    });

    if (load) {
      getComponentsByProductId(allowBlank);
    }
  }
}

// Stolen from http://stackoverflow.com/questions/133925/javascript-post-request-like-a-form-submit
function postToURL(path, params, method) {
  method = method || 'post'; // Set method to post by default, if not specified.

  // The rest of this code assumes you are not using a library.
  // It can be made less wordy if you use one.
  let form = document.createElement('form');
  form.setAttribute('method', method);
  form.setAttribute('action', path);

  let hiddenField = null;

  for(let key in params) {
    if (typeof params[key] === 'object') {
      for (let i in params[key]) {
        if (typeof params[key][i] !== 'string') {
          continue;
        }

        hiddenField = document.createElement('input');
        hiddenField.setAttribute('type', 'hidden');
        hiddenField.setAttribute('name', key);
        hiddenField.setAttribute('value', params[key][i]);
        form.appendChild(hiddenField);
      }
    } else {
      hiddenField = document.createElement('input');
      hiddenField.setAttribute('type', 'hidden');
      hiddenField.setAttribute('name', key);
      hiddenField.setAttribute('value', params[key]);
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
        'source': function (request, response) {
          sendHTMLRequest({
            url: '/management/getinfo/',
            data: {
              name__startswith: request.term,
              info_type: 'tags',
              format: 'ulli',
              field: 'name'
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

      jQ('#id_tag_form').on('submit', function (e) {
        e.stopPropagation();
        e.preventDefault();

        constructTagZone(container, Nitrate.Utils.formSerialize(this));
      });

      jQ('#tag_count').text(jQ('tbody#tag').prop('count'));
    },
  });
}


function addTag(container) {
  let tagName = jQ('#id_tags').prop('value');
  if (!tagName.length) {
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
  let nt = prompt(defaultMessages.prompt.edit_tag, tag);
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

/**
 * Update one object property at a time.
 * @param {string} contentType
 * @param {number} objectPk
 * @param {string} field
 * @param {string} value
 * @param {string} valueType
 * @param {function} [callback] - a function will be called when AJAX request succeeds. This
 *                                function should accept only one argument, that is the parsed JSON
 *                                data returned from server side. If omitted, it will cause
 *                                undefined is passed to postRequest, and default behavior of
 *                                reloading current page will be triggered as a result.
 */
function updateObject(contentType, objectPk, field, value, valueType, callback) {
  postRequest({
    url: '/ajax/update/',
    success: callback,
    data: {
      content_type: contentType,
      object_pk: Array.isArray(objectPk) ? objectPk.join(',') : objectPk,
      field: field,
      value: value,
      value_type: valueType || 'str'
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
function constructForm(content, action, formObserve, info, s, c) {
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
    c.on('click', function () {
      clearDialog();
    });
  }

  if (formObserve) {
    f.on('submit', formObserve);
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
  let contentContainer = options.expandPaneContainer;
  let blindIcon = container.find('img.blind_icon');
  if (contentContainer.css('display') === 'none') {
    blindIcon.removeClass('collapse').addClass('expand').prop('src', '/static/images/t1.gif');
  } else {
    blindIcon.removeClass('expand').addClass('collapse').prop('src', '/static/images/t2.gif');
  }
}

function blinddownAllCases(element) {
  jQ('img.expand').each(function () {
    jQ(this).trigger('click');
  });
  if (element) {
    jQ(element)
      .removeClass('collapse-all').addClass('expand-all')
      .prop('src', '/static/images/t2.gif');
  }
}

function blindupAllCases(element) {
  jQ('.collapse').each(function () {
    jQ(this).trigger('click');
  });

  if (element) {
    jQ(element)
      .removeClass('expand-all').addClass('collapse-all')
      .prop('src', '/static/images/t1.gif');
  }
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

function renderComponentForm(container, parameters, formObserve) {
  let d = jQ('<div>');
  if (!container) {
    container = getDialog();
  }
  jQ(container).show();

  postHTMLRequest({
    url: '/cases/get-component-form/',
    data: parameters,
    container: d,
    callbackAfterFillIn: function () {
      let a = jQ('<input>', {'type': 'submit', 'value': 'Add'});
      let c = jQ('<label>');
      c.append(a);
      jQ(container).html(
        constructForm(
          d.html(), '/cases/add-component/', formObserve,
          'Press "Ctrl" to select multiple default component', c[0]
        )
      );
      bindComponentSelectorToProduct(
        false, false, jQ('#id_product')[0], jQ('#id_o_component')[0]
      );
    }
  });
}


