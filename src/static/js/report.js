Nitrate.Report = {};
Nitrate.Report.List = {};
Nitrate.Report.CustomSearch = {};
Nitrate.Report.CustomDetails = {};

Nitrate.Report.List.on_load = function () {};

Nitrate.Report.Builds = {};

Nitrate.Report.Builds.on_load = function () {
  if (jQ('#report_build').length) {
    jQ('#report_build').dataTable({
      'bPaginate': false,
      'bFilter': false,
      'bProcessing': true,
      'oLanguage': {'sEmptyTable': 'No build was found in this product.'}
    });
  }
};

Nitrate.Report.CustomSearch.on_load = function () {
  let productSelect = document.getElementById('id_product');

  bindBuildSelectorToProduct(
    productSelect, document.getElementById('id_pk__in'), false
  );
  bindVersionSelectorToProduct(
    productSelect, document.getElementById('id_build_run__product_version'), true
  );
  bindCategorySelectorToProduct(
    productSelect, document.getElementById('id_testcaserun__case__category'), true
  );
  bindComponentSelectorToProduct(
    productSelect, document.getElementById('id_testcaserun__case__component'), true
  );

  jQ('#id_product').trigger('change');

  if (jQ('#id_table_report').length) {
    jQ('#id_table_report').dataTable({
      'aoColumnDefs':[{'sType': 'numeric', 'aTargets': [1, 2, 3, 4, 5 ]}],
      'bPaginate': false,
      'bFilter': false,
      'bProcessing': true,
      'oLanguage': {'sEmptyTable': 'No report data was found.'}
    });
  }

  jQ('.build_link').on('click', function (e) {
    e.stopPropagation();
    e.preventDefault();
    let params = Nitrate.Utils.formSerialize(jQ('#id_form_search')[0]);
    params.pk__in = jQ(this).siblings().eq(0).val();

    postToURL(this.href, params, 'get');
  });
};

Nitrate.Report.CustomDetails.on_load = function () {
  bindBuildSelectorToProduct(
    document.getElementById('id_product'),
    document.getElementById('id_pk__in'),
    false
  );
};
