function deleConfirm(attachment_id, home, plan_id) {
  if (!window.confirm("Are you sure to delete the attachment?")) {
    return false;
  }

  jQ.ajax({
    url: '/management/deletefile/',
    type: 'POST',
    dataType: 'json',
    data: {file_id: attachment_id, from_plan: plan_id},
    success: function(data, textStatus, jqXHR) {
      jQ('#' + attachment_id).remove();
      jQ('#attachment_count').text(parseInt(jQ('#attachment_count').text()) - 1);
    },
    error: function (jqXHR, textStatus, errorThrown) {
      window.alert(jqXHR.responseJSON.message);
    }
  });
}
