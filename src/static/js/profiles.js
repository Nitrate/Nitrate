Nitrate.Profiles = {Infos: {}, Bookmarks: {}};

Nitrate.Profiles.Bookmarks.on_load = function () {
  if (jQ('#id_table_bookmark').length) {
    jQ('#id_table_bookmark').dataTable({
      'aoColumnDefs':[{'bSortable':false, 'aTargets':[ 0 ]}],
      'aaSorting': [[ 1, 'asc' ]],
      'sPaginationType': 'full_numbers',
      'bFilter': false,
      'aLengthMenu': [[10, 20, 50, -1], [10, 20, 50, 'All']],
      'iDisplayLength': 10,
      'bProcessing': true,
      'oLanguage': {'sEmptyTable': 'No bookmark was found.'},
      'fnDrawCallback': function () {
        jQ('#id_table_bookmark tbody tr td:nth-child(1)').shiftcheckbox({
          checkboxSelector: ':checkbox',
          selectAll: '#id_table_bookmark .js-select-all'
        });
      }
    });
  }

  jQ('#id_form_bookmark').on('submit', function (e) {
    e.stopPropagation();
    e.preventDefault();

    if (!window.confirm(defaultMessages.confirm.remove_bookmark)) {
      return false;
    }

    let parameters = Nitrate.Utils.formSerialize(this);
    if (parameters.pk === undefined) {
      showModal('No bookmark selected.');
      return false;
    }

    postRequest({url: this.action, data: parameters, traditional: true});
  });
};
