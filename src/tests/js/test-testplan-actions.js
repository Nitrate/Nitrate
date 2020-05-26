QUnit.module('testplan_action.js', function () {
  QUnit.module('Test getSelectedCaseIDs', function () {
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
  });
});
