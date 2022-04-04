function setCookie(name, value, expires, path, domain, secure) {
  document.cookie = name + '=' + escape(value) +
    ((expires) ? '; expires=' + expires.toGMTString() : '') +
    ((path) ? '; path=' + path : '') +
    ((domain) ? '; domain=' + domain : '') +
    ((secure) ? '; secure' : '');
}

function checkCookie() {
  let exp = new Date();
  exp.setTime(exp.getTime() + 1800000);
  // first write a test cookie
  setCookie('cookies', 'cookies', exp, false, false, false);
  if (document.cookie.indexOf('cookies') !== -1) {
    // now delete the test cookie
    exp = new Date();
    exp.setTime(exp.getTime() - 1800000);
    setCookie('cookies', 'cookies', exp, false, false, false);

    return true;
  } else {
    return false;
  }
}

jQ(window).on('load', function () {
  if (!checkCookie()) {
    jQ('#login_info').html(
      '<font color="red">Browser cookie support maybe disabled, please enable it for login.</font>'
    );
    jQ('#login_info').parent().show();
    jQ('#id_login_form').prop('disabled', true);
  }

  if (jQ('#id_username').length) {
    jQ('#id_password').on('keydown', keydownPassword);
  }
});

function loginTCMS() {
  let username = jQ('#id_username').val().replace(/\040/g, '').replace(/%20/g, '');
  if (username.length === 0) {
    jQ('#id_username').effect('shake', 100).focus();
    return false;
  }
  jQ('#id_login_form').submit();
}

function keydownPassword(event) {
  if (event.which === 13) {
    loginTCMS();
  }
}
