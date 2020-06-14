jQ(function () {
  // event listening for form submission
  jQ('#btnSearchPlan').click(function () {
    jQ('#inpTarget').val('plan');
    jQ('#frmSearch').submit();
  });
  jQ('#btnSearchCase').click(function () {
    jQ('#inpTarget').val('case');
    jQ('#frmSearch').submit();
  });
  jQ('#btnSearchRun').click(function () {
    jQ('#inpTarget').val('run');
    jQ('#frmSearch').submit();
  });

  registerProductAssociatedObjectUpdaters(
    document.getElementById('pl_product'),
    false,
    [
      {
        func: getVersionsByProductId,
        targetElement: document.getElementById('pl_version'),
        addBlankOption: false
      },
      {
        func: getComponentsByProductId,
        targetElement: document.getElementById('pl_component'),
        addBlankOption: false
      }
    ]
  );

  registerProductAssociatedObjectUpdaters(
    document.getElementById('r_product'),
    false,
    [
      {
        func: getVersionsByProductId,
        targetElement: document.getElementById('r_version'),
        addBlankOption: false
      },
      {
        func: getBuildsByProductId,
        targetElement: document.getElementById('r_build'),
        addBlankOption: false
      }
    ]
  );

  registerProductAssociatedObjectUpdaters(
    document.getElementById('cs_product'),
    false,
    [
      {
        func: getComponentsByProductId,
        targetElement: document.getElementById('cs_component'),
        addBlankOption: false
      },
      {
        func: getCategoriesByProductId,
        targetElement: document.getElementById('cs_category'),
        addBlankOption: false
      }
    ]
  );
});
