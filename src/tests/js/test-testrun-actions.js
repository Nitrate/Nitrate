QUnit.module('testrun_action.js', function () {
  QUnit.module('Test getSelectedCaseRunIDs', function () {
    let containerId = 'id_table_cases';

    QUnit.testStart(function () {
      let div = document.createElement('div');
      div.id = containerId;
      document.body.appendChild(div);

      let input = null;
      for (let i = 1; i < 6; i++) {
        input = document.createElement('input');
        input.type = 'checkbox';
        input.id = 'case_run_' + i.toString();
        input.value = i.toString();
        input.name = 'case_run';
        div.appendChild(input);
      }
    });

    QUnit.testDone(function () {
      document.body.removeChild(document.getElementById(containerId));
    });

    QUnit.test('Return an empty array if no case run is checked', function (assert) {
      let result = getSelectedCaseRunIDs();  /* eslint no-undef:off */
      assert.ok(result.length === 0);
    });

    QUnit.test('Return the selected case runs', function (assert) {
      document.getElementById('case_run_1').checked = true;
      document.getElementById('case_run_3').checked = true;

      let result = getSelectedCaseRunIDs();
      assert.deepEqual(result, ['1', '3']);
    });
  });
});
