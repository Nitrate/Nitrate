QUnit.module('testplan_action.js', function () {

  QUnit.module('Test getSelectedCaseIDs');

  QUnit.test('get selected case IDs', function (assert) {
    let container = jQ(
      '<div>' +
      '<input type="checkbox" name="case" value="1" checked>' +
      '<input type="checkbox" name="case" value="2">' +
      '<input type="checkbox" name="case" value="3" checked>' +
      '</div>'
    );
    assert.deepEqual(getSelectedCaseIDs(container[0]), ['1', '3']);
  });

  QUnit.test('no case is selected', function (assert) {
    let container = jQ(
      '<div>' +
      '<input type="checkbox" name="case" value="1">' +
      '<input type="checkbox" name="case" value="2">' +
      '</div>'
    );
    assert.deepEqual(getSelectedCaseIDs(container[0]), []);
  });

  QUnit.test('all cases are selected', function (assert) {
    let container = jQ(
      '<div>' +
      '<input type="checkbox" name="case" value="1" checked>' +
      '<input type="checkbox" name="case" value="2" checked>' +
      '</div>'
    );
    assert.deepEqual(getSelectedCaseIDs(container[0]), ['1', '2']);
  });

  QUnit.module('Test tree view', {
    beforeEach: function () {
      // Initialize the treeview element like this:
      // <div id="plans-treeview" class="js-plans-treeview"></div>
      let treeViewDiv = document.createElement('div');
      treeViewDiv.id = 'plans-treeview';
      treeViewDiv.setAttribute('class', 'js-plans-treeview');
      let container = document.getElementById('treeview');
      container.appendChild(treeViewDiv);
    },
    afterEach: function () {
      document
        .getElementById('treeview')
        .removeChild(document.getElementById('plans-treeview'));
    }
  });

  // Sample tree view
  // plan 1
  //   plan 2
  //     plan 3
  //       plan 4
  //         plan 5
  //         plan 6
  //       plan 7
  //     plan 8
  const jsTreeConfig = {
    core: {
      data: [
        {id: '1', parent: '#', text: 'plan 1'},
        {id: '2', parent: '1', text: 'plan 2'},
        {id: '3', parent: '2', text: 'plan 3'},
        {id: '4', parent: '3', text: 'plan 4'},
        {id: '5', parent: '4', text: 'plan 5'},
        {id: '6', parent: '4', text: 'plan 6'},
        {id: '7', parent: '3', text: 'plan 7'},
        {id: '8', parent: '2', text: 'plan 8'}
      ]
    }
  };

  QUnit.test('get direct descendants', function (assert) {
    let done = assert.async();
    jQ('#treeview .js-plans-treeview')
      .jstree(jsTreeConfig)
      .on('ready.jstree', function () {
        document.getElementById('treeview-current-plan-id').value = '3';
        let directDescendants = Nitrate.TestPlans.TreeView.getDescendants(true);
        assert.deepEqual(directDescendants, [4, 7]);
        done();
      });
  });

  QUnit.test('get descendants from all depth', function (assert) {
    let done = assert.async();
    jQ('#treeview .js-plans-treeview')
      .jstree(jsTreeConfig)
      .on('ready.jstree', function () {
        document.getElementById('treeview-current-plan-id').value = '3';
        let descendants = Nitrate.TestPlans.TreeView.getDescendants();
        assert.deepEqual(descendants, [4, 5, 6, 7]);
        done();
      });
  });

  QUnit.test('get ancestors', function (assert) {
    let done = assert.async();
    jQ('#treeview .js-plans-treeview')
      .jstree(jsTreeConfig)
      .on('ready.jstree', function () {
        document.getElementById('treeview-current-plan-id').value = '7';
        let ancestors = Nitrate.TestPlans.TreeView.getAncestors();
        assert.deepEqual(ancestors.sort(), [1, 2, 3]);
        done();
      });
  });

});
