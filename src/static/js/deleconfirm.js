/* eslint no-redeclare: "off" */
/* eslint no-unused-vars: "off" */

function deleConfirm(attachmentId, home, planId) {
  if (!window.confirm('Are you sure to delete the attachment?')) {
    return false;
  }

  postRequest({
    url: '/management/deletefile/',
    data: {file_id: attachmentId, from_plan: planId},
    success: function () {
      jQ('#' + attachmentId).remove();
      jQ('#attachment_count').text(parseInt(jQ('#attachment_count').text()) - 1);
    },
  });
}
