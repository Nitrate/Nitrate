// require tcms_actions

Nitrate.Attachments = {
  on_load: function () {
    let self = this;
    jQ('table#attachments .js-remove').on('click', function (e) {
      let data = e.target.dataset;
      self.removeAttachment(parseInt(data.attachmentId), data.from, parseInt(data.objectId));
    });
  },

  /**
   * Remove an attachment and update the attachment count if there is in the document.
   *
   * @param {number} attachmentId - the attachment id.
   * @param {string} from - what the attachment is associated with. Valid values are from_plan and from_case.
   * @param {number} objectId - the associated plan or case id.
   */
  removeAttachment: function (attachmentId, from, objectId) {
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
}
