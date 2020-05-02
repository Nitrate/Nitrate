jQ(window).on('load', function() {
  if (!checkCookie()) {
    jQ('#login_info').html("<font color=\"red\">Browser cookie support maybe disabled, please enable it for login.</font>");
    jQ('#login_info').parent().show();
    jQ('#id_login_form').attr('disabled', true);
  }

  if (jQ('#id_username').length) {
    jQ('#id_password').on('keydown', keydownPassword);
  }
});

function loginTCMS() {
  let username = jQ('#id_username').val().replace(/\040/g, "").replace(/%20/g, "");
  if (username.length === 0) {
    jQ("#id_username").effect('shake', 100).focus();
    return false;
  }
  jQ('#id_login_form').submit();
}

function keydownUserName(event) {
  if (event.which === 13) {
    jQ('#id_password').focus();
  }
}

function keydownPassword(event) {
  if (event.which === 13) {
    loginTCMS();
  }
}
