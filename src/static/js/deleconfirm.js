/* eslint no-redeclare: "off" */

function deleConfirm(attachmentId, from, objectId) {
  confirmDialog({
    message: 'Are you sure to delete the attachment?',
    title: 'Manage attachments',
    yesFunc: function () {
      let data = {file_id: attachmentId};
      switch (from) {
        case 'from_case':
          data.from_case = objectId;
          break;
        case 'from_plan':
          data.from_plan = objectId;
          break;
        default:
          throw new Error('Argument home has invalid value "' + from + '"');
      }
      postRequest({
        url: '/management/deletefile/',
        data: data,
        success: function () {
          jQ('#' + attachmentId).remove();
          jQ('#attachment_count').text(parseInt(jQ('#attachment_count').text()) - 1);
        },
      });
    }
  });
}
