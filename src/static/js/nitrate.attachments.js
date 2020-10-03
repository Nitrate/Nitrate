Nitrate.Attachments = {
  on_load: function () {
    jQ('table#attachments .js-remove').on('click', function () {
      let params = jQ(this).data('params');
      deleConfirm(params[0], params[1], params[2]);
    });
  }
}
