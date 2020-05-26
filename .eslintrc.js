module.exports = {
  "env": {
    "browser": true,
    "es6": true,
    "jquery": true,
    "qunit": true
  },
  "extends": "eslint:recommended",
  "globals": {
    "Atomics": "readonly",
    "SharedArrayBuffer": "readonly",

    // vendors
    "Handlebars": "readonly",
    "SelectBox": "readonly",
    "SelectFilter": "readonly",
    "TableDnD": "readonly",

    "bind_build_selector_to_product": "readonly",
    "getComponentsByProductId": "readonly",
    "getCategoriesByProductId": "readonly",
    "bind_category_selector_to_product": "readonly",
    "bind_component_selector_to_product": "readonly",
    "bind_version_selector_to_product": "readonly",
    "blinddownAllCases": "readonly",
    "blindupAllCases": "readonly",
    "clearDialog": "readonly",
    "clickedSelectAll": "readonly",
    "constructForm": "readonly",
    "constructTagZone": "readonly",
    "default_messages": "readonly",
    "deleConfirm": "readonly",
    "fireEvent": "readonly",
    "getAjaxLoading": "readonly",
    "getDialog": "readonly",
    "getRequest": "readonly",
    "globalCsrfToken": "readonly",
    "id_to_windowname": "readonly",
    "jQ": "readonly",
    "Nitrate": "writable",
    "popupAddAnotherWindow": "readonly",
    "postHTMLRequest": "readonly",
    "postRequest": "readonly",
    "postToURL": "readonly",
    "previewPlan": "readonly",
    "removeComment": "readonly",
    "renderComponentForm": "readonly",
    "sendHTMLRequest": "readonly",
    "setUpChoices": "readonly",
    "submitComment": "readonly",
    "toggleExpandArrow": "readonly",
    "toggleTestCasePane": "readonly",
    "updateObject": "readonly",
    "getSelectedCaseIDs": "readonly",
    "splitString": "readonly",
    "SHORT_STRING_LENGTH": "readonly",
  },
  "parserOptions": {
    "ecmaVersion": 2018
  },
  "rules": {
  }
};
