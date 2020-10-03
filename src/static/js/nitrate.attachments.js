Nitrate.Attachments = {
  on_load: function () {
    jQ('table#attachments .js-remove').on('click', function (e) {
      let data = e.target.dataset;
      deleConfirm(parseInt(data.attachmentId), data.from, parseInt(data.objectId));
    });
  }
}
