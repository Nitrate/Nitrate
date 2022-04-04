/* eslint no-redeclare: "off" */

// Create a dictionary to avoid polluting the global namespace:
const Nitrate = window.Nitrate || {}; // Ironically, this global name is not respected. So u r on ur own.
window.Nitrate = Nitrate;

Nitrate.Utils = {};
const SHORT_STRING_LENGTH = 100;

const RIGHT_ARROW = '/static/images/t1.gif';
const DOWN_ARROW = '/static/images/t2.gif';

/**
 * @constant {number}
 * @default
 */
const SORT_KEY_MIN = 0

/**
 * @constant {number}
 * @default
 */
const SORT_KEY_MAX = 32300


/**
 * Check if a given sort key is in allowed range.
 *
 * @param {number} sortKey - a given sort key to test.
 * @returns {boolean} true if the sort key is in the allowed range, otherwise false is returned.
 */
function isSortKeyInAllowedRange(sortKey) {
  return sortKey >= SORT_KEY_MIN && sortKey <= SORT_KEY_MAX
}

/**
 * Utility function.
 * Set up a function callback for after the page has loaded
 *
 * @param {Function} callback - a callback function that will be called at
 *                              window.load event.
 */
// FIXME: the callback should not be registered to window.on_load event directly.
// By doing that, the callback's this is modified that brings extra effort to handle the this object.
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
 *
 * @param {HTMLFormElement} f - A HTML form from where to collect data.
 * @returns {object} a mapping containing form data.
 */
Nitrate.Utils.formSerialize = function (f) {
  let data = {};
  jQ(f).serializeArray().forEach(function (field) {
    let name = field.name;
    let existingValue = data[field.name];
    if (existingValue === undefined) {
      data[name] = field.value;
    } else {
      if (! Array.isArray(existingValue)) {
        data[name] = [existingValue];
      }
      data[name].push(field.value);
    }
  });
  return data;
};

/**
 * Change objects order sort key.
 *
 * @param {Function} changeOrderRequestFunc
 *   a function to be called to send an HTTP request to change test case order (the sort key).
 * @param {number} [curSortKey=undefined]
 *   the current sort key of the order to be shown in the prompt input dialog.
 */
Nitrate.Utils.changeOrderSortKey = function (changeOrderRequestFunc, curSortKey) {
  let promptDefault = curSortKey !== undefined ? curSortKey.toString() : undefined;
  let userInput = window.prompt('Enter a new sort key', promptDefault);
  if (!userInput || userInput.length === 0) {
    return;
  }

  let msg = 'The input sort key ' + userInput + ' must be a number and limited in ' +
    '[' + SORT_KEY_MIN.toString() + ', ' + SORT_KEY_MAX.toString() + '].'
  if (! /^\d+$/.test(userInput)) {
    showModal(msg, 'Invalid sort key');
    return;
  }

  let newSortKey = parseInt(userInput);
  if (newSortKey === curSortKey) {
    showModal('You have input a same sort key. Nothing changed.', 'Change Order');
    return;
  }
  if (!isSortKeyInAllowedRange(newSortKey)) {
    showModal(msg, 'Invalid sort key');
    return;
  }

  changeOrderRequestFunc(newSortKey);
}

/**
 * Return the CSRF token generated for POST HTTP request.
 *
 * This requires the CSRF token is generated in the DOM.
 *
 * @return {string} the CSRF token.
 */
function getAjaxCsrfToken() {
  return document.getElementById('ajaxCsrfToken')
    .querySelector('[name=csrfmiddlewaretoken]').value;
}

/**
 * Simple wrapper of jQuery.ajax to add header for CSRF.
 *
 * @param {string} url - a url passed to url argument of jQuery $.ajax
 * @param {object} options - the options passed to options argument of jQuery $.ajax
 */
function $ajax(url, options) {
  options = Object.assign({}, options, {
    beforeSend: function (xhr, settings) {
      if (!/^(GET|HEAD|OPTIONS|TRACE)$/.test(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader('X-CSRFToken', getAjaxCsrfToken());
      }
    },
  });
  jQ.ajax(url, options);
}

function ajaxHandler500(options) {
  if (options.errorMessage !== undefined) {
    showModal(options.errorMessage);
    return;
  }

  showModal(
    'Something wrong in the server. Please contact administrator to deal with this issue.'
  );
}

function ajaxHandler400(options, xhr) {
  if (options.errorMessage !== undefined) {
    showModal(options.errorMessage);
    return;
  }
  if (options.badRequestMessage !== undefined) {
    showModal(options.badRequestMessage);
    return;
  }

  let data = JSON.parse(xhr.responseText);
  // response property will be deprecated from server response.
  // TODO: after the AJAX response is unified, just use the responseJSON.message.
  let msg = data.message || data.response || data.messages || data;
  if (Array.isArray(msg)) {
    showModal(msg.join('\n'));
  } else {
    showModal(msg);
  }
}

function ajaxHandler403(options) {
  showModal(
    options.forbiddenMessage || 'You are not allowed to perform this operation.'
  );
}

/**
 * Send a AJAX request to the backend server and handle the response. The response from backend is
 * expected to be in JSON data format.
 *
 * @param {object} options - configure the jQuery.ajax call.
 * @param {string} options.url - url of the resource.
 * @param {string} [options.method] - type of the request. Default is POST.
 * @param {object} [options.data] - request data.
 * @param {string} [options.contentType] - content type of the request body.
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
 * @param {Function} [options.success] - hook to success option of jQuery.ajax. If omitted, a
 *                                       default callback will be hooked to reload the page.
 */
function sendAjaxRequest(options) {
  const ajaxOptions = {
    type: options.method || 'post',
    dataType: 'json',
    data: options.data,
    async: !options.sync,
    success: options.success || function () { window.location.reload(); },
    statusCode: {
      500: function () { ajaxHandler500(options); },
      // How about 404?
      //
      400: function (xhr) { ajaxHandler400(options, xhr); },
      403: function () { ajaxHandler403(options); }
    }
  }
  // Setting contentType is primarily for the PATCH request.
  if (options.contentType) {
    ajaxOptions.contentType = options.contentType;
  }
  if (options.traditional) {
    ajaxOptions.traditional = options.traditional;
  }
  $ajax(options.url, ajaxOptions);
}

/**
 * Wrapper of sendAjaxRequest to send an HTTP GET request.
 *
 * @param {object} options - options for making a GET request.
 */
function getRequest(options) {
  let forwardOptions = Object.assign({}, options, {'method': 'GET'})
  sendAjaxRequest(forwardOptions);
}

/**
 * Wrapper of sendAjaxRequest to send an HTTP POST request.
 *
 * @param {object} options - options for making a POST request.
 */
function postRequest(options) {
  let forwardOptions = Object.assign({}, options, {'method': 'POST'})
  sendAjaxRequest(forwardOptions);
}

/**
 * Wrapper of sendAjaxRequest to send an HTTP PATCH request.
 *
 * @param {object} options - options for making a PATCH request.
 */
function patchRequest(options) {
  let forwardOptions = Object.assign({}, options, {
    'method': 'PATCH',
    'contentType': 'application/json',
    'processData': false,
  });
  forwardOptions.data = JSON.stringify(forwardOptions.data);
  sendAjaxRequest(forwardOptions);
}

/**
 * Send request and expect server responses content in HTML.
 *
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
 * @param {Function} [options.success] - hook to success option of jQuery.ajax. If omitted, a
 *                                       default callback will be hooked to fill the content
 *                                       returned from server side in the specified container
 *                                       element and invoke the callback if specified.
 * @param {HTMLElement} [options.container] - an HTML container element which the content
 *                                            returned from server will be filled in.
 * @param {Function} [options.callbackAfterFillIn] - a function will be called after the returned
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
        showModal(
          options.notFoundMessage ||
          xhr.responseText ||
          'Requested resource is not found.'
        );
      },
      400: function (xhr) {
        showModal(
          options.badRequestMessage ||
          xhr.responseText ||
          'The request is invalid to be processed by the server.'
        );
      },
      403: function (xhr) {
        showModal(
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
});

const defaultMessages = {
  'alert': {
    'no_case_selected': 'No cases selected! Please select at least one case.',
    'no_category_selected': 'No category selected! Please select a category firstly.',
    'ajax_failure': 'Communication with server got some unknown errors.',
    'tree_reloaded': 'The tree has been reloaded.',
    'last_case_run': 'It is the last case run',
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
      cases_component: '/cases/component/',
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

function splitString(str, num) {
  if (str.length > num) {
    return str.substring(0, num - 3) + '...';
  }
  return str;
}

/**
 * Clear all options from a give SELECT element.
 *
 * @param {HTMLSelectElement} selectElement - the SELECT element from which to remove all options.
 */
function emptySelect(selectElement) {
  let i = selectElement.options.length;
  while (--i >= 0) {
    selectElement.options[i].remove();
  }
}

/**
 * Setup option of a given select element in place. The original selection is preserved.
 *
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

  emptySelect(elemSelect);

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

/**
 * Request builds associated with product and update the build select list
 *
 * @param {string[]} productIds - the product ids.
 * @param {HTMLSelectElement} buildSelect - requested builds will be filled into this select element.
 * @param {boolean} addBlankOption - indicate whether to add a blank option.
 */
function getBuildsByProductId(productIds, buildSelect, addBlankOption) {
  let data = {info_type: 'builds', product_id: productIds}

  if (jQ('#value_sub_module').val() === 'new_run') {
    // The backend only checks if is_active appears in the request and whatever
    // the value it has.
    data.is_active = '1'
  }

  getRequest({
    url: '/management/getinfo/',
    data: data,
    traditional: true,
    errorMessage: 'Update builds failed.',
    success: function (data) {
      setUpChoices(
        buildSelect,
        data.map(function (o) { return [o.pk, o.fields.name]; }),
        addBlankOption
      );

      if (jQ('#value_sub_module').length && jQ('#value_sub_module').val() === 'new_run') {
        if(jQ(buildSelect).html() === '') {
          showModal('You should create new build first before create new run');
        }
      }
    },
  });
}

/**
 * Update product version select list according to a specific product
 *
 * @param {string[]} productIds - the product ids.
 * @param {HTMLSelectElement} versionSelect - the SELECT element of product version.
 * @param {boolean} addBlankOption - indicate whether to add a blank option.
 */
function getVersionsByProductId(productIds, versionSelect, addBlankOption) {
  getRequest({
    url: '/management/getinfo/',
    data: {info_type: 'versions', product_id: productIds},
    traditional: true,
    success: function (data) {
      setUpChoices(
        versionSelect,
        data.map(function (o) { return [o.pk, o.fields.value]; }),
        addBlankOption
      );
    },
    errorMessage: 'Update versions failed.',
  });
}

/**
 * Update associated components of a specific product
 *
 * @param {string[]} productIds - the product Id to update the associated components.
 * @param {HTMLSelectElement} componentSelect - fill the returned components into this select
 *                                              element.
 * @param {boolean} addBlankOption - indicate whether to display a blank option.
 * @param {Function} [callback] - a function called after requested components are filled in.
 */
function getComponentsByProductId(productIds, componentSelect, addBlankOption, callback) {
  getRequest({
    url: '/management/getinfo/',
    data: {info_type: 'components', product_id: productIds},
    traditional: true,
    errorMessage: 'Update components failed.',
    success: function (data) {
      setUpChoices(
        componentSelect,
        data.map(function (o) { return [o.pk, o.fields.name]; }),
        addBlankOption
      );

      if (callback) { callback(); }
    },
  });
}

/**
 * Refresh categories related to a product and fill in a SELECT element.
 *
 * @param {string[]} productIds - the product Id used to update associated categories.
 * @param {HTMLSelectElement} categorySelect - the category element to fill in.
 * @param {boolean} addBlankOption - whether to add a special option item to SELECT as a blank
 *                                   selected option.
 */
function getCategoriesByProductId(productIds, categorySelect, addBlankOption) {
  getRequest({
    url: '/management/getinfo/',
    data: {info_type: 'categories', product_id: productIds},
    traditional: true,
    errorMessage: 'Update category failed.',
    success: function (data) {
      setUpChoices(
        categorySelect,
        data.map(function (o) {return [o.pk, o.fields.name];}),
        addBlankOption
      );
    },
  });
}

/**
 * Register updaters to update associated objects when select specific product options.
 *
 * @param {HTMLElement} productSelect - the product SELECT element. Associated objects are changed
 *                                      accordingly when select one or more options.
 * @param {boolean} triggerProductSelect - whether to trigger the product SELECT element change
 *                                         event immediately just after binding the change event handler.
 * @param {object[]} updaters - list of updater information.
 * @param {Function} updaters.func - the function to be called to get associated objects from server side, and then
 *                                   fill in the target element. This function must have three arguments, the first one
 *                                   accepts selected product IDs from the product element, the second one accepts
 *                                   the target element, and the last one indicates whether to add a blank option.
 * @param {HTMLElement} updaters.targetElement - the target element to fill in with the associated objects.
 * @param {boolean} updaters.addBlankOption - whether to add a blank option as the first option. This will be passed to
 */
function registerProductAssociatedObjectUpdaters(productSelect, triggerProductSelect, updaters) {
  jQ(productSelect).on('change', function () {
    let selectedOptions = [];
    for (let i = 0; i < this.selectedOptions.length; i++) {
      selectedOptions.push(this.selectedOptions.item(i));
    }
    let hasEmptySelection = selectedOptions.filter(function (option) {return option.value === '';}).length > 0;

    if (selectedOptions.length === 0 || hasEmptySelection) {
      updaters.forEach(function (updaterInfo) {
        setUpChoices(updaterInfo.targetElement, [], true);
      });
      return;
    }

    let selectedProductIds = selectedOptions.map(function (option) {return option.value;});
    updaters.forEach(function (updaterInfo) {
      updaterInfo.func(selectedProductIds, updaterInfo.targetElement, updaterInfo.addBlankOption);
    });
  })

  if (triggerProductSelect) {
    jQ('#id_product').trigger('change');
  }
}

// Stolen from http://stackoverflow.com/questions/133925/javascript-post-request-like-a-form-submit
/**
 * Make an HTTP request by simulating a form submission
 *
 * @param {string} path - this is the form action.
 * @param {object} params - the form data.
 * @param {string} [method=post] - get or post. Defaults to post.
 */
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

  if (method === 'post') {
    let csrfTokenHidden = document.createElement('input');
    csrfTokenHidden.setAttribute('type', 'hidden');
    csrfTokenHidden.setAttribute('name', 'csrfmiddlewaretoken');
    csrfTokenHidden.setAttribute('value', getAjaxCsrfToken());
    form.appendChild(csrfTokenHidden);
  }

  document.body.appendChild(form);    // Not entirely sure if this is necessary
  form.submit();
}

/**
 * Preview Plan
 *
 * @param {object} parameters - parameters to request plans for preview.
 * @param {string} action - same as the argument action of function constructForm.
 * @param {Function} callback - a function with only one event argument will be bound to a HTMLFormElement submit event.
 * @param {string} notice - a text message displayed in the plans preview dialog.
 * @param {HTMLElement} [submitButton=null] - directly pass to the argument submitButton of constructForm.
 *                                            Deprecated, this argument is not used anymore.
 * @param {HTMLElement} [cancelButton=null] - directly pass to the argument cancelButton of constructForm.
 *                                            Deprecated, this argument is not used anymore.
 */
function previewPlan(parameters, action, callback, notice, submitButton, cancelButton) {
  let dialog = getDialog();
  clearDialog();
  jQ(dialog).show();

  sendHTMLRequest({
    url: '/plans/preview/',
    data: Object.assign({}, parameters),
    success: function (data, textStatus, xhr) {
      jQ(dialog).html(
        constructForm(xhr.responseText, action, callback, notice, submitButton, cancelButton)
      );
    },
  });
}

/**
 * Create an AJAX loading element.
 *
 * @param {string} [id] - the new element id.
 * @returns {HTMLElement} the new element.
 */
function constructAjaxLoading(id) {
  let div = document.createElement('div');
  div.setAttribute('class', 'ajax_loading');
  if (id !== undefined && id.length) {
    div.id = id;
  }
  return div;
}

/**
 * Create an INPUT element.
 *
 * @param {string} type - the type attribute.
 * @param {string} name - the name attribute.
 * @param {string} value - the value attribute.
 * @returns {HTMLInputElement} the created INPUT element.
 */
function createInputElement(type, name, value) {
  const elem = document.createElement('input');
  elem.type = type;
  elem.name = name;
  elem.value = value;
  return elem;
}

/**
 * Construct an HTML form element.
 *
 * @param {string} content - the content displayed in the constructed form.
 * @param {string} action - the endpoint passed to form element's action attribute.
 * @param {Function} [formObserve=null] - an optional function bound to the generated form's submit event.
 * @param {string} [info=''] - a text message displayed in the form.
 * @param {HTMLElement} [submitButton=null] - the submit button to submit the constructed form.
 * @param {HTMLElement} [cancelButton=null] - the cancel button to close the dialog containing the constructed form.
 * @returns {HTMLFormElement} - the constructed form element.
 */
function constructForm(content, action, formObserve, info, submitButton, cancelButton) {
  const form = document.createElement('form');
  form.action = action;
  const infoSection = document.createElement('div');
  infoSection.className = 'alert';

  if (info) {
    infoSection.appendChild(document.createTextNode(info));
  }

  if (! submitButton) {
    submitButton = createInputElement('submit', '_submit', 'Submit');
  }

  if (! cancelButton) {
    cancelButton = createInputElement('button', 'cancel', 'Cancel');
    cancelButton.addEventListener('click', () => {
      clearDialog();
    });
  }

  if (formObserve) {
    form.addEventListener('submit', formObserve);
  }

  form.insertAdjacentHTML('afterbegin', content);
  form.appendChild(infoSection);
  form.appendChild(submitButton);
  form.appendChild(cancelButton);

  return form;
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

function blinddownAllCases(element) {
  jQ('img.expand').each(function () {
    jQ(this).trigger('click');
  });
  if (element) {
    jQ(element)
      .removeClass('collapse-all').addClass('expand-all')
      .prop('src', DOWN_ARROW);
  }
}

function blindupAllCases(element) {
  jQ('.collapse').each(function () {
    jQ(this).trigger('click');
  });

  if (element) {
    jQ(element)
      .removeClass('expand-all').addClass('collapse-all')
      .prop('src', RIGHT_ARROW);
  }
}

function renderComponentForm(container, parameters, formObserve) {
  if (!container) {
    container = getDialog();
  }
  jQ(container).show();

  const div = document.createElement('div');

  postHTMLRequest({
    url: '/cases/get-component-form/',
    data: parameters,
    container: div,
    callbackAfterFillIn: function () {
      const label = document.createElement('label');
      const submitButton = createInputElement('submit', 'addComponents', 'Add');
      label.appendChild(submitButton);

      jQ(container).html(
        constructForm(
          div.innerHTML, '/cases/add-component/', formObserve,
          'Press "Ctrl" to select multiple default component', label
        )
      );
      registerProductAssociatedObjectUpdaters(
        document.getElementById('id_product'),
        false,
        [
          {
            func: getComponentsByProductId,
            targetElement: document.getElementById('id_o_component'),
            addBlankOption: false
          }
        ]
      );
    }
  });
}

/************ Dialog operations *****************/

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

  jQ(dialog).html(constructAjaxLoading());
  return jQ(dialog).hide()[0];
}

/**
 * Show a modal dialog.
 *
 * @param {string} showMessage - show this message in the modal dialog.
 * @param {string} [title] - the dialog title.
 */
function showModal(showMessage, title) {
  let pDialogShowMessage = document.getElementById('dialogShowMessage');
  pDialogShowMessage.appendChild(document.createTextNode(showMessage));
  jQ('#messageDialog')
    .prop('title', title || '')
    .dialog({
      modal: true,
      dialogClass: 'hide-titlebar-close',
      buttons: {
        Ok: function () {
          pDialogShowMessage.removeChild(pDialogShowMessage.firstChild);
          jQ(this).dialog('close');
          jQ(this).dialog('destroy');
        }
      }
    });
}

/**
 * Show confirmation dialog with a specific message.
 *
 * @param {object} options - options to show a confirm dialog.
 * @param {string} options.message - the message to be shown in the dialog.
 * @param {string} [options.title] - dialog title.
 * @param {Function} [options.yesFunc] - the function to be called when click Yes button.
 */
function confirmDialog(options) {
  let messageElem = document.getElementById('confirmMessage');
  let textNode = messageElem.firstChild;
  if (textNode) {
    messageElem.removeChild(messageElem.firstChild);
  }
  messageElem.appendChild(document.createTextNode(options.message));

  jQ('#confirmDialog').dialog({
    resizable: false,
    height: 'auto',
    width: 400,
    modal: true,
    dialogClass: 'hide-titlebar-close',
    title: options.title || '',
    buttons: {
      Yes: function () {
        if (options.yesFunc) {
          options.yesFunc();
        }
        jQ(this).dialog('destroy');
      },
      No: function () {
        jQ(this).dialog('destroy');
      }
    }
  });
}

Nitrate.DataTable = {
  commonSettings: {
    aLengthMenu: [[10, 20, 50, -1], [10, 20, 50, 'All']],
    bFilter: false,
    bInfo: true,
    bLengthChange: false,
    bProcessing: true,
    bServerSide: true,
    iDisplayLength: 20,
    sPaginationType: 'full_numbers',

    fnInitComplete: function (oSettings, json) {
      if (oSettings.aoData.length > 1) {
        return;
      }
      // If table is empty or only has a single row, ensure sortable columns
      // are set to unsortable in order to avoid potential unnecessary HTTP
      // request made by clicking header by user.
      let columns = oSettings.aoColumns;
      for (let i = 0; i < columns.length; i++) {
        let column = columns[i];
        if (column.bSortable) {
          column.bSortable = false;
        }
      }
    },
  }
};


/**
 * A base tags view.
 *
 * The implementation of the tags views is closely related to the existing functionalities inside
 * the tags table and UL list in a specific plan, case and run.
 *
 * @class
 */
class TagsBaseView {
  /**
   * Construct a tags view object.
   *
   * @param {number|string} objectId - the object id whose tags are managed in this view.
   */
  constructor(objectId) {
    this.objectId = objectId;
    this.addEndpoint = this.removeEndpoint = '/management/tags/';
  }

  /**
   * Get the HTML element containing the tags view.
   *
   * @returns {HTMLElement} the HTML element representing the container.
   */
  getContainer() {
    return document.getElementById('tag');
  }
}

/**
 * A tags table view.
 *
 * This class provides common functions to operate tags.
 *
 * @class
 */
class TagsTableView extends TagsBaseView {
  /**
   * Construct a tags table view object.
   *
   * @param {number|string} objectId - the object id whose tags are managed in this view.
   */
  constructor(objectId) {
    super(objectId);
    this.getEndpoint = '/management/tags/';
  }

  /**
   * Bind event handlers on the elements inside the view.
   */
  bindEventHandlers() {
    let self = this;

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
      self.addTag();
    });

    jQ('.js-remove-tag').on('click', function () {
      let thisTag = jQ(this).parents('.js-one-tag').data('param');
      self.removeTag(thisTag);
    });

    jQ('.js-edit-tag').on('click', function () {
      let thisTag = jQ(this).parents('.js-one-tag').data('param');
      self.editTag(thisTag);
    });

    jQ('#js-add-tag').on('click', function () {
      self.addTag();
    });

    jQ('#tag_count').text(jQ('#id_tag_form').find('tbody').data('count'));
  }


  /**
   * Get the HTTP request data to get tags.
   *
   * Both plan and case tags view class have to implement this method to provide
   * specific data, which should include plan or case id.
   */
  getGetRequestData() {
    throw new Error('Must be implemented in subclass.');
  }


  /**
   * Send an HTTP GET request to get and show the tags.
   */
  get() {
    let self = this;
    sendHTMLRequest({
      url: self.getEndpoint,
      data: self.getGetRequestData(),
      container: self.getContainer(),
      callbackAfterFillIn: function () {
        self.bindEventHandlers();
      }
    });
  }


  /**
   * Get the data from the form.
   *
   * @returns {object} the form data.
   */
  getFormData() {
    let form = document.getElementById('id_tag_form')
      , inputs = form.elements
      , numInputs = inputs.length
      , data = {}
      ;
    for (let i = 0; i < numInputs; i++) {
      let elem = inputs[i];
      data[elem.name] = elem.value;
    }
    return data;
  }


  /**
   * Add a tag.
   *
   * @param {string} [tag] - optionally specify a tag to add.
   * @param {Function} [successCallback]
   *   an optional callback function to be called after the tags are shown. This
   *   argument is added and intented to be used with the argument tag together to
   *   implement the editTag function.
   */
  addTag(tag, successCallback) {
    let self = this
      , container = self.getContainer()
      , formData = this.getFormData()
      ;

    formData.a = 'add';
    if (tag) {
      formData.tags = tag;
    }

    jQ(container).html(constructAjaxLoading());
    postHTMLRequest({
      url: self.addEndpoint,
      data: formData,
      container: container,
      callbackAfterFillIn: function () {
        self.bindEventHandlers();
        if (successCallback) {
          successCallback();
        }
      }
    });
  }

  /**
   * Edit a tag.
   *
   * @param {string} originalTag - the tag to be edited. Note that, this tag is not actually be
   *   edited. Instead, this edit operation will add a new tag and remove this originalTag.
   */
  editTag(originalTag) {
    let newTag = prompt(defaultMessages.prompt.edit_tag, originalTag);
    if (!newTag || newTag === originalTag) {
      return;
    }

    let self = this;

    this.addTag(newTag, function () {
      self.removeTag(originalTag);
    });
  }

  /**
   * Remove tag.
   *
   * @param {string} tag - remove this tag from the object.
   */
  removeTag(tag) {
    let self = this
      , container = self.getContainer()
      , formData = this.getFormData()
      ;

    formData.a = 'remove';
    formData.tags = tag;

    jQ(container).html(constructAjaxLoading());
    postHTMLRequest({
      url: self.removeEndpoint,
      data: formData,
      container: container,
      callbackAfterFillIn: function () {
        self.bindEventHandlers();
      }
    });
  }
}

/**
 * A tags view representing the tags table inside a test case Web page.
 */
class CaseTagsView extends TagsTableView {
  /**
   * Return the GET HTTP request data to get the tags table.
   *
   * For a test case, the HTTP request requires passing the case id in argument `case`.
   *
   * @returns {object} the data containing case id to get tags.
   */
  getGetRequestData() {
    return {case: this.objectId};
  }
}

/**
 * A tags view representing the tags table inside a test plan Web page.
 */
class PlanTagsView extends TagsTableView {
  /**
   * Return the GET HTTP request data to get the tags table.
   *
   * For a test plan, the HTTP request requires passing the plan id in argument `plan`.
   *
   * @returns {object} the data containing plan id to get tags.
   */
  getGetRequestData() {
    return {plan: this.objectId};
  }
}

// UL list view inside a test run page

/**
 * A tags view representing the UL list inside a test run Web page.
 */
class RunTagsView extends TagsBaseView {
  /**
   * Return the container element including the UL list of tags.
   *
   * @returns {HTMLElement} the container element.
   */
  getContainer() {
    return jQ('.js-tag-ul')[0];
  }

  /**
   * Add a tag to the UL list.
   */
  addTag() {
    let self = this;
    let newTag = window.prompt('Please type new tag.');
    if (! newTag) {
      return;
    }
    postHTMLRequest({
      url: this.addEndpoint,
      data: {a: 'add', run: this.objectId, tags: newTag},
      container: self.getContainer(),
      callbackAfterFillIn: function () {
        self.bindEventHandlers();
      }
    });
  }

  /**
   * Remove a tag from the UL list.
   *
   * @param {string} tag - the tag to be removed.
   */
  removeTag(tag) {
    let self = this;
    postHTMLRequest({
      url: this.removeEndpoint,
      data: {a: 'remove', run: this.objectId, tags: tag},
      container: self.getContainer(),
      callbackAfterFillIn: function () {
        self.bindEventHandlers();
      }
    });
  }

  /**
   * Bind event handlers on the elements which manipulate tags.
   */
  bindEventHandlers() {
    jQ('.js-add-tag').on('click', function () {
      let view = new RunTagsView(this.dataset.runId);
      view.addTag();
    });

    let container = this.getContainer();
    jQ(container).find('.js-remove-tag').on('click', function () {
      let view = new RunTagsView(this.dataset.runId);
      view.removeTag(this.dataset.tag);
    });
  }
}
