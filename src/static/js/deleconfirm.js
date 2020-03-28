function deleConfirm(attachment_id, home, plan_id) {
  let answer = window.confirm("Arey you sure to delete the attachment?");
  if (!answer) {
    return false;
  }

  jQ.ajax({
    'url': "/management/deletefile/" + attachment_id + "?" + home + "=" + plan_id,
    'type': 'GET',
    'success': function(data, textStatus, jqXHR) {
      let returnobj = jQ.parseJSON(jqXHR.responseText);
      if (returnobj.rc === 0) {
        jQ('#' + attachment_id).remove();
        jQ('#attachment_count').text(parseInt(jQ('#attachment_count').text()) - 1);
      } else if (returnobj.response === 'auth_failure') {
        window.alert('Permission denied!');
      } else {
        window.alert('Server Exception');
      }
    }
  });
}

