Nitrate.Report = {};
Nitrate.Report.List = {};
Nitrate.Report.CustomSearch = {};
Nitrate.Report.CustomDetails = {};

Nitrate.Report.List.on_load = function(){
	
}

Nitrate.Report.Builds = {};

Nitrate.Report.Builds.on_load = function() {
  if (jQ('#report_build').length) {
    jQ('#report_build').dataTable({
      "bPaginate": false,
      "bFilter": false,
      "bProcessing": true,
      "oLanguage": { "sEmptyTable": "No build was found in this product." }
    });
  }
};

Nitrate.Report.CustomSearch.on_load = function() {
  if (jQ('#id_pk__in').length) {
    bind_build_selector_to_product(false, jQ('#id_product')[0], jQ('#id_pk__in')[0]);
  }

  if (jQ('#id_build_run__product_version').length) {
    bind_version_selector_to_product(true, false, jQ('#id_product')[0], jQ('#id_build_run__product_version')[0]);
  }

  if (jQ('#id_testcaserun__case__category').length) {
    bind_category_selector_to_product(true, false, jQ('#id_product')[0], jQ('#id_testcaserun__case__category')[0]);
  }

  if (jQ('#id_testcaserun__case__component').length) {
    bind_component_selector_to_product(true, false, jQ('#id_product')[0], jQ('#id_testcaserun__case__component')[0]);
  }
};

Nitrate.Report.CustomDetails.on_load = function() {
  if (jQ('#id_pk__in').length) {
    bind_build_selector_to_product(false, jQ('#id_product')[0], jQ('#id_pk__in')[0]);
  }

  if (jQ('#id_build_run__product_version').length) {
    bind_version_selector_to_product(true, false, jQ('#id_product')[0], jQ('#id_build_run__product_version')[0]);
  }
};
