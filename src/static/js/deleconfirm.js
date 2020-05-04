function deleConfirm(attachment_id, home, plan_id) {
  if (!window.confirm("Are you sure to delete the attachment?")) {
    return false;
  }

  postRequest({
    url: '/management/deletefile/',
    data: {file_id: attachment_id, from_plan: plan_id},
    success: function() {
      jQ('#' + attachment_id).remove();
      jQ('#attachment_count').text(parseInt(jQ('#attachment_count').text()) - 1);
    },
  });
}
