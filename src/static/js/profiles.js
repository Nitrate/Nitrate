Nitrate.Profiles = { Infos: {}, Bookmarks: {} };

Nitrate.Profiles.Bookmarks.on_load = function() {
  if (jQ('#id_table_bookmark').length) {
    jQ('#id_table_bookmark').dataTable({
      "aoColumnDefs":[{ "bSortable":false, "aTargets":[ 0 ] }],
      "aaSorting": [[ 1, "asc" ]],
      "sPaginationType": "full_numbers",
      "bFilter": false,
      "aLengthMenu": [[10, 20, 50, -1], [10, 20, 50, "All"]],
      "iDisplayLength": 10,
      "bProcessing": true,
      "oLanguage": { "sEmptyTable": "No bookmark was found." }
    });
  }

  if (jQ('#id_check_all_bookmark').length) {
    jQ('#id_check_all_bookmark').on('click', function(e) {
      clickedSelectAll(this, jQ('#id_table_bookmark')[0], 'pk');
    });
  }

  jQ('#id_form_bookmark').on('submit', function(e) {
    e.stopPropagation();
    e.preventDefault();

    if (!window.confirm(default_messages.confirm.remove_bookmark)) {
      return false;
    }

    let parameters = Nitrate.Utils.formSerialize(this);
    if (parameters.pk === undefined) {
      window.alert('No bookmark selected.');
      return false;
    }

    postRequest({url: this.action, data: parameters, traditional: true});
  });
};
