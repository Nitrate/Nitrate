function getProdRelatedObj(prodIDs, target, targetID) {
  prodIDs = Array.isArray(prodIDs) ? prodIDs : [prodIDs];
  // Separator , used to join/split values
  getRequest({
    url: '/ajax/get-prod-relate-obj/',
    data: {'p_ids': prodIDs.join(','), 'target': target, 'sep': ','},
    success: function(data){
      buildOptions(data, targetID);
    }
  });
}

function buildOptions(data, target) {
  // target should be the ID of a select tag
  let options = [];
  for(let i=0;i<data.length;i++){
    let pair = data[i];
    options.push('<option value="' + pair[0] + '">' + pair[1] + '</option>');
  }
  options = options.join();
  jQ('#'+target).html(options);
}

/*
 * @ target: component, version, category, build
 * @ productID: select tag
 * @ target select tag
 */
function updateOptionOnProdChange(target, productID, targetID) {
  jQ('#' + productID).change(function() {
    getProdRelatedObj(jQ('#' + productID).val(), target, targetID);
  });

  // whether get related objects immediately
  let isTargetEmpty = jQ('#' + targetID + ' option').length === 0;
  let prodIDs = jQ('#' + productID).val();
  if (prodIDs && isTargetEmpty) {
    getProdRelatedObj(prodIDs, target, targetID);
  }
}

jQ(function() {
  // event listening for form submission
  jQ('#btnSearchPlan').click(function() {
    jQ('#inpTarget').val('plan');
    jQ('#frmSearch').submit();
  });
  jQ('#btnSearchCase').click(function() {
    jQ('#inpTarget').val('case');
    jQ('#frmSearch').submit();
  });
  jQ('#btnSearchRun').click(function() {
    jQ('#inpTarget').val('run');
    jQ('#frmSearch').submit();
  });
});

jQ(function() {
  // product select on change event binding
  updateOptionOnProdChange('version', 'pl_product', 'pl_version');
  updateOptionOnProdChange('version', 'r_product','r_version');
  updateOptionOnProdChange('build', 'r_product', 'r_build');
  updateOptionOnProdChange('component', 'pl_product', 'pl_component');
  updateOptionOnProdChange('component', 'cs_product', 'cs_component');
  updateOptionOnProdChange('category', 'cs_product', 'cs_category');
});
