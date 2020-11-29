/* eslint no-redeclare:off */
/* eslint no-unused-vars:off */
const globalCsrfToken = '1234';

QUnit.module('tcms_actions.js', function () {

  QUnit.module('Test setUpChoices', function () {
    QUnit.test('simple basic setup', function (assert) {
      let options = [['1', 'case 1'], ['2', 'case 2'], ['3', 'case 3']];
      let select = jQ('<select name="test_setup_choices"></select>')[0];

      setUpChoices(select, options, false);

      assert.equal(options.length, select.options.length);
      for (let i = 0; i < select.options.length; i++) {
        let addOption = select.options[i];
        assert.equal(options[i][0], addOption.value);
        assert.equal(options[i][1], addOption.text);
      }
    });

    QUnit.test('add a blank option', function (assert) {
      let options = [['1', 'case 1']];
      let select = jQ('<select name="test_setup_choices"></select>')[0];

      setUpChoices(select, options, true);

      let addedOption = select.options[0];
      assert.equal('', addedOption.value);
      assert.equal('---------', addedOption.text);

      addedOption = select.options[1];
      assert.equal('1', addedOption.value);
      assert.equal('case 1', addedOption.text);
    });

    QUnit.test('empty options', function (assert) {
      let select = jQ('<select name="test_setup_choices"></select>')[0];
      setUpChoices(select, [], false);
      assert.equal(0, select.options.length);
    });

    QUnit.test('preserve selected option', function (assert) {
      let select =
        jQ('<select name="test_setup_choices">' +
          '<option value="1">case 1</option>'  +
          '<option value="2" selected>case 2</option>'  +
          '</select>')[0];

      setUpChoices(select, [['1', 'preserve option'], ['2', 'case 2']], false);

      assert.equal(2, select.options.length);

      let addedOption = select.options[0];
      assert.equal('1', addedOption.value);
      assert.equal('preserve option', addedOption.text);
      assert.notOk(addedOption.selected);

      addedOption = select.options[1];
      assert.equal('2', addedOption.value);
      assert.equal('case 2', addedOption.text);
      assert.ok(addedOption.selected);
    });

    QUnit.test('shorten long option text', function (assert) {
      let select = jQ('<select name="test_setup_choices"></select>')[0];
      let longText = 'abc'.repeat(SHORT_STRING_LENGTH);
      setUpChoices(select, [['1', longText]], false);

      let addedOption = select.options[0];
      assert.equal('1', addedOption.value);
      assert.equal(splitString(longText, SHORT_STRING_LENGTH), addedOption.text);
      assert.equal(longText, addedOption.title);
    });
  });

  QUnit.module('Test Nitrate.Utils.formSerialize', function () {
    QUnit.test('serialize form controls', function (assert) {
      let form = jQ(
        '<form>' +
        '<input type="checkbox" name="case" value="1" checked>' +
        '<input type="checkbox" name="case" value="2" checked>' +
        '<input type="text" name="summary" value="test">' +
        '<select name="lang">' +
        '<option value="python" selected>Python</option>' +
        '<option value="js">JavaScript</option>' +
        '</select>' +
        '</form>'
      );

      let result = Nitrate.Utils.formSerialize(form[0]);
      assert.deepEqual(result, {case: ['1', '2'], summary: 'test', lang: 'python'});
    });

    QUnit.test('serialize form controls without checked controls', function (assert) {
      let form = jQ(
        '<form>' +
        '<input type="checkbox" name="case" value="1">' +
        '<input type="checkbox" name="case" value="2">' +
        '<input type="text" name="summary" value="test">' +
        '<select name="lang">' +
        '<option value="python" selected>Python</option>' +
        '<option value="js">JavaScript</option>' +
        '</select>' +
        '</form>'
      );

      let result = Nitrate.Utils.formSerialize(form[0]);
      assert.deepEqual(result, {summary: 'test', lang: 'python'});
    });
  });

  QUnit.module('Test updateObject', function () {
    QUnit.testDone(function () {
      jQ.mockjax.clear();
    });

    QUnit.test('use default url', function (assert) {
      jQ.mockjax({
        url: '/ajax/update/',
        type: 'POST',
        data: function (data) {
          let expected = {
            content_type: 'testplans.testplan', object_pk: '1', field: 'type',
            value: '2', value_type: 'int'
          };
          assert.deepEqual(data, expected);
          return true;
        }
      });

      updateObject({
        contentType: 'testplans.testplan', field: 'type', objectPk: '1',
        value: '2', valueType: 'int',
      });
    });

    QUnit.test('update multiple objects', function (assert) {
      jQ.mockjax({
        url: '/ajax/update/',
        type: 'POST',
        data: function (data) {
          let expected = {
            content_type: 'testplans.testplan', object_pk: '1,2,3', field: 'type',
            value: '2', value_type: 'int'
          };
          assert.deepEqual(data, expected);
          return true;
        }
      });

      updateObject({
        contentType: 'testplans.testplan', field: 'type', objectPk: ['1', '2', '3'],
        value: '2', valueType: 'int',
      });
    });

    QUnit.test('update a string property', function (assert) {
      jQ.mockjax({
        url: '/ajax/update/',
        type: 'POST',
        data: function (data) {
          let expected = {
            content_type: 'testplans.testplan', object_pk: '1', field: 'summary',
            value: 'new summary', value_type: 'str'
          };
          assert.deepEqual(data, expected);
          return true;
        }
      });

      updateObject({
        contentType: 'testplans.testplan', field: 'summary', objectPk: '1',
        value: 'new summary',
      });
    });

    QUnit.test('specify the update endpoint explicitly', function (assert) {
      jQ.mockjax({
        url: '/test/update-object/',
        type: 'POST',
        data: function (data) {
          let expected = {
            content_type: 'testplans.testplan', object_pk: '1', field: 'type',
            value: '1', value_type: 'int'
          };
          assert.deepEqual(data, expected);
          return true;
        }
      });

      updateObject({
        url: '/test/update-object/',
        contentType: 'testplans.testplan', field: 'type', objectPk: '1',
        value: '1', valueType: 'int'
      });
    });
  });

  QUnit.module('Test constructAjaxLoading', function () {
    QUnit.test('create without id', function (assert) {
      let elem = constructAjaxLoading();
      assert.ok(elem.hasAttribute('class'));
      assert.equal(elem.getAttribute('class'), 'ajax_loading');
    });

    QUnit.test('create with id', function (assert) {
      let id = 'id_loading';
      let elem = constructAjaxLoading(id);
      assert.equal(elem.id, id);
    });
  });
});
