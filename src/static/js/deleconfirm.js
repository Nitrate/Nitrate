function deleConfirm(attachment_id, home, plan_id) {
  let answer = window.confirm("Arey you sure to delete the attachment?");
  if (!answer) {
    return false;
  }

  jQ.ajax({
    'url': "/management/deletefile/" + attachment_id + "?" + home + "=" + plan_id,
    'type': 'GET',
    'dataType': 'json',
    'success': function(data, textStatus, jqXHR) {
      if (data.rc === 0) {
        jQ('#' + attachment_id).remove();
        jQ('#attachment_count').text(parseInt(jQ('#attachment_count').text()) - 1);
      } else if (data.response === 'auth_failure') {
        window.alert('Permission denied!');
      } else {
        window.alert('Server Exception');
      }
    }
  });
}

