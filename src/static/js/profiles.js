Nitrate.Profiles = { Infos: {}, Bookmarks: {} };

Nitrate.Profiles.Bookmarks.on_load = function() {

	var bookmarksTable = jQ("#bookmarks_table").DataTable({
		"columnDefs": [
			{ "orderable": false, "targets": 0 }
		],
		dom: "ti",
		language: {
			zeroRecords: "No bookmark was found."
		},
    paging: false,
    searching: false,
		order: [[ 1, 'asc' ]],
  });

  jQ('#selectAll').bind('click', function(e) {
    var selectAll = e.target.checked;
    jQ('.js-select-bookmark').prop('checked', selectAll);
    jQ('#removeSelectedBookmarks').prop('disabled', !selectAll);
  });

  jQ('.js-select-bookmark').bind('click', function(e) {
    var checkedValues = jQ('.js-select-bookmark').map(function() {
      return jQ(this).prop('checked');
    }).get();

    jQ('#selectAll').prop('checked', checkedValues.reduce(function(a, b) {return a && b}));
    jQ('#removeSelectedBookmarks').prop('disabled', checkedValues.indexOf(true) < 0);
  });

  jQ('#removeSelectedBookmarks').bind('click', function(e) {
    var form = jQ('#bookmarkActionForm');
    jQ('#bookmarks_table .js-select-bookmark').each(function() {
      var checkbox = jQ(this);
      if (checkbox.prop('checked')) {
        jQ('<input>').attr({
          type: 'hidden',
          value: checkbox.val(),
          name: 'bookmark_id'
        }).prependTo(form);
      }
    });
    form.submit();
  });
};