module.exports = {
  'plugins': [
    'jsdoc'
  ],
  'env': {
    'browser': true,
    'es6': true,
    'jquery': true,
    'qunit': true
  },
  'extends': [
    'eslint:recommended',
    'plugin:jsdoc/recommended'
  ],
  'globals': {
    'Atomics': 'readonly',
    'SharedArrayBuffer': 'readonly',

    // vendors
    'Handlebars': 'readonly',
    'SelectBox': 'readonly',
    'SelectFilter': 'readonly',
    'TableDnD': 'readonly',

    'jQ': 'readonly',
    'Nitrate': 'writable',

    'SORT_KEY_MIN': 'readonly',
    'SORT_KEY_MAX': 'readonly',
    'isSortKeyInAllowedRange': 'readonly',

    'getBuildsByProductId': 'readonly',
    'getCategoriesByProductId': 'readonly',
    'getComponentsByProductId': 'readonly',
    'getVersionsByProductId': 'readonly',
    'registerProductAssociatedObjectUpdaters': 'readonly',

    'getRequest': 'readonly',
    'patchRequest': 'readonly',
    'postHTMLRequest': 'readonly',
    'postRequest': 'readonly',
    'postToURL': 'readonly',
    'sendHTMLRequest': 'readonly',

    'removeComment': 'readonly',
    'submitComment': 'readonly',
    'updateCommentsCount': 'readonly',

    'CaseTagsView': 'readonly',
    'PlanTagsView': 'readonly',
    'RunTagsView': 'readonly',

    'blinddownAllCases': 'readonly',
    'blindupAllCases': 'readonly',
    'clearDialog': 'readonly',
    'confirmDialog': 'readonly',
    'constructAjaxLoading': 'readonly',
    'constructForm': 'readonly',
    'defaultMessages': 'readonly',
    'emptySelect': 'readonly',
    'getDialog': 'readonly',
    'getSelectedCaseIDs': 'readonly',
    'globalCsrfToken': 'readonly',
    'id_to_windowname': 'readonly',
    'popupAddAnotherWindow': 'readonly',
    'previewPlan': 'readonly',
    'renderComponentForm': 'readonly',
    'setUpChoices': 'readonly',
    'showModal': 'readonly',
    'SHORT_STRING_LENGTH': 'readonly',
    'splitString': 'readonly',
    'updateObject': 'readonly',

    'createInputElement': 'readonly',
  },
  'parserOptions': {
    'ecmaVersion': 2018
  },
  'rules': {
    'brace-style': ['error', '1tbs', {'allowSingleLine': true}],
    'camelcase': ['error', {'properties': 'never'}],
    'comma-spacing': 'error',
    'curly': 'error',
    'eqeqeq': 'error',
    'func-call-spacing': 'error',
    'func-style': ['error', 'declaration'],
    'indent': ['error', 2, {'SwitchCase': 1}],
    'linebreak-style': ['error', 'unix'],
    'max-len': ['error', {'code': 120, 'ignoreUrls': true}],
    'no-trailing-spaces': 'error',
    'no-unused-vars': ['error', {'caughtErrors': 'none', 'vars': 'local', 'args': 'none'}],
    'no-var': 'error',
    'object-curly-spacing': 'error',
    'operator-linebreak': ['error', 'after'],
    'quotes': ['error', 'single', {'avoidEscape': true}],
    'space-before-function-paren': ['error', {'anonymous': 'always', 'named': 'never', 'asyncArrow': 'always'}],
    'space-infix-ops': 'error',
    'jsdoc/require-jsdoc': 0
  }
};
