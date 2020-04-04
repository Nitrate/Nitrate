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

    jQ.ajax({
      'url': this.action,
      'type': this.method,
      'data': parameters,
      'dataType': 'json',
      'traditional': true,
      'success': function (data, textStatus, jqXHR) {
        if (data.rc !== 0) {
          window.alert(data.response);
          return data;
        }
        // using location.reload will cause firefox(tested) remember the checking status
        window.location = window.location;
      },
      'error': function (jqXHR, textStatus, errorThrown) {
        json_failure(jqXHR);
      }
    });
  });
};
