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

    "jQ": "readonly",
    "Nitrate": "writable",

    "getBuildsByProductId": "readonly",
    "getCategoriesByProductId": "readonly",
    "getComponentsByProductId": "readonly",
    "getVersionsByProductId": "readonly",
    "registerProductAssociatedObjectUpdaters": "readonly",

    "getRequest": "readonly",
    "postHTMLRequest": "readonly",
    "postRequest": "readonly",
    "postToURL": "readonly",
    "sendHTMLRequest": "readonly",

    "blinddownAllCases": "readonly",
    "blindupAllCases": "readonly",
    "clearDialog": "readonly",
    "constructForm": "readonly",
    "constructTagZone": "readonly",
    "defaultMessages": "readonly",
    "deleConfirm": "readonly",
    "getAjaxLoading": "readonly",
    "getDialog": "readonly",
    "getSelectedCaseIDs": "readonly",
    "globalCsrfToken": "readonly",
    "id_to_windowname": "readonly",
    "popupAddAnotherWindow": "readonly",
    "previewPlan": "readonly",
    "removeComment": "readonly",
    "renderComponentForm": "readonly",
    "setUpChoices": "readonly",
    "SHORT_STRING_LENGTH": "readonly",
    "splitString": "readonly",
    "submitComment": "readonly",
    "toggleExpandArrow": "readonly",
    "toggleTestCasePane": "readonly",
    "updateObject": "readonly",
  },
  "parserOptions": {
    "ecmaVersion": 2018
  },
  "rules": {
    "brace-style": ["error", "1tbs", {"allowSingleLine": true}],
    "camelcase": ["error", {"properties": "never"}],
    "curly": "error",
    "eqeqeq": "error",
    "func-style": ["error", "declaration"],
    "indent": ["error", 2, {"SwitchCase": 1}],
    "linebreak-style": ["error", "unix"],
    "no-var": "error",
    "quotes": ["error", "single", {"avoidEscape": true}],
    "object-curly-spacing": "error",
    "operator-linebreak": ["error", "after"],
    "func-call-spacing": "error",
    "no-trailing-spaces": "error",
    "space-before-function-paren": ["error", {"anonymous": "always", "named": "never", "asyncArrow": "always"}],
    "comma-spacing": "error",
    "space-infix-ops": "error",
  }
};
