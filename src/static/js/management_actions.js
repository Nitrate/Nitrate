Nitrate.Management = {};
Nitrate.Management.Environment = {};

const MgtEnv = Nitrate.Management.Environment;

Nitrate.Management.Environment.Edit = {
  on_load: function () {
    SelectFilter.init('id_properties', 'properties', 0, '/static/admin/');

    jQ('#js-edit-group').submit(function (e) {
      e.preventDefault();
      let form = jQ(this);
      postHTMLRequest({
        url: form.prop('action'),
        data: form.serialize(),
        success: function () {
          window.location = '/environment/groups/';
        },
      });
    });

    jQ('#js-back-button').click(function () {
      window.location = '/environment/groups/';
    });
  }
};

Nitrate.Management.Environment.Groups = {
  on_load: function () {
    jQ('#changelist-search').on('submit', function (e) {
      if (jQ(e.target).find('input[name=name]').val().trim() === '') {
        return false;
      }
    });

    jQ('a.loglink').on('click', function () {
      jQ(this).parents('.js-env-group').next().toggle();
    });

    jQ('.js-add-env-group').on('click', function () {
      Nitrate.Management.Environment.Groups.addEnvGroup();
    });

    jQ('.js-del-env-group').on('click', function () {
      let params = jQ(this).parents('.js-env-group').data('params');
      Nitrate.Management.Environment.Groups.deleteEnvGroup(params[0], params[1]);
    });

    jQ('.js-enable-env-group').on('click', function () {
      let params = jQ(this).parents('.js-env-group').data('params');
      Nitrate.Management.Environment.Groups.setEnvGroupStatus(params[0], 1)
    });

    jQ('.js-disable-env-group').on('click', function () {
      let params = jQ(this).parents('.js-env-group').data('params');
      Nitrate.Management.Environment.Groups.setEnvGroupStatus(params[0], 0)
    });
  },

  /**
   * Add a new environment group.
   */
  addEnvGroup: function () {
    let groupName = window.prompt('New environment group name').trim();
    if (!groupName) {
      return;
    }

    postRequest({
      url: Nitrate.Management.Environment.Groups.URLs.add_group,
      data: {'name': groupName},
      forbiddenMessage: 'You are not allowed to add an environment group.',
      success: function (data) {
        let url = Nitrate.Management.Environment.Groups.URLs.edit_group;
        window.location.href = url.replace('$id', data.env_group_id);
      },
    });
  },

  /**
   * Delete an environment group.
   * @param {number} envGroupId
   * @param {string} envGroupName
   */
  deleteEnvGroup: function (envGroupId, envGroupName) {
    confirmDialog({
      message: 'Are you sure you wish to remove environment group - ' + envGroupName,
      title: 'Manage Environment Group',
      yesFunc: function () {
        postRequest({
          url: Nitrate.Management.Environment.Groups.URLs.delete_group.replace('$id', envGroupId),
          forbiddenMessage: 'You are not allowed to delete an environment group.',
          success: function () {
            jQ('#' + envGroupId).remove();
          },
        });
      }
    });
  },

  /**
   * Enable or disable an environment group.
   * @param {number} envGroupID
   * @param {number} status - 0 for disable and 1 for enable.
   */
  setEnvGroupStatus: function (envGroupID, status) {
    let url = Nitrate.Management.Environment.Groups.URLs.set_group_status.replace('$id', envGroupID);
    postRequest({
      url: url,
      data: {status: status},
      forbiddenMessage: 'You are not allowed to set status for an environment group.',
      success: function (data) {
        if (status === 0) {
          jQ('.js-enable-env-group').removeClass('hidden');
          jQ('.js-disable-env-group').addClass('hidden');
          // The first child HTMLLabelElement contains the group name
          jQ('#' + data.env_group_id).find('label').addClass('line-through');
        } else {
          jQ('.js-enable-env-group').addClass('hidden');
          jQ('.js-disable-env-group').removeClass('hidden');
          jQ('#' + data.env_group_id).find('label').removeClass('line-through');
        }
      },
    });
  },
};

Nitrate.Management.Environment.Property = {
  on_load: function () {
    jQ('#js-add-prop').on('click', function () {
      Nitrate.Management.Environment.Property.addEnvProperty();
    });
    jQ('#js-disable-prop').on('click', function () {
      Nitrate.Management.Environment.Property.setEnvPropertyStatus(0);
    });
    jQ('#js-enable-prop').on('click', function () {
      Nitrate.Management.Environment.Property.setEnvPropertyStatus(1);
    });
    jQ('.js-prop-name').on('click', function () {
      Nitrate.Management.Environment.Property.selectEnvProperty(
        parseInt(jQ(this).parents('.js-one-prop').data('param'))
      );
    });
    jQ('.js-edit-prop').on('click', function () {
      Nitrate.Management.Environment.Property.editEnvProperty(
        parseInt(jQ(this).parents('.js-one-prop').data('param'))
      );
    });

    jQ('#id_properties_container :checkbox').shiftcheckbox();
  },

  /**
   * Select environment property
   * @param {number} propertyId
   */
  selectEnvProperty: function (propertyId) {
    jQ('#id_properties_container li.focus').removeClass('focus');
    jQ('#id_property_' + propertyId).addClass('focus');

    sendHTMLRequest({
      url: MgtEnv.Property.URLs.list_property_values.replace('$id', propertyId),
      container: jQ('#' + 'id_values_container'),
      callbackAfterFillIn: MgtEnv.PropertyValue.bindPropertyValueActions,
      notFoundMessage: 'Cannot find environment property with id ' + propertyId.toString(),
    });
  },

  /**
   * Edit an environment property
   * @param {number} id
   */
  editEnvProperty: function (id) {
    let newPropertyName = window.prompt('New property name', jQ('#id_property_name_' + id).html());
    if (!newPropertyName) {
      return;
    }

    let urls = Nitrate.Management.Environment.Property.URLs;

    postRequest({
      url: urls.edit_property.replace('$id', id),
      data: {id: id, name: newPropertyName},
      forbiddenMessage: 'You are not allowed to add environment property.',
      success: function (data) {
        jQ('#id_property_name_' + id).html(data.name);
      },
    });
  },

  /**
   * Add an environment property.
   */
  addEnvProperty: function () {
    let propertyName = window.prompt('New property name');
    if (!propertyName) {
      return;
    }

    let urls = Nitrate.Management.Environment.Property.URLs;
    postRequest({
      url: urls.add_property,
      data: {name: propertyName},
      forbiddenMessage: 'You are not allowed to add environment property.',
      success: function (data) {
        jQ('#id_properties_container li.focus').removeClass('focus');

        let template = Handlebars.compile(jQ('#properties_container_template').html());
        let context = {'id': data.id, 'name': data.name};
        jQ('#id_properties_container')
          .append(template(context)).find('.js-prop-name').on('click', function () {
            Nitrate.Management.Environment.Property.selectEnvProperty(
              parseInt(jQ(this).parent().data('param'))
            );
          })
          .end().find('.js-rename-prop').on('click', function () {
            Nitrate.Management.Environment.Property.editEnvProperty(
              parseInt(jQ(this).parent().data('param'))
            );
          });

        Nitrate.Management.Environment.Property.selectEnvProperty(data.id);
      },
    });
  },

  /**
   * Disable selected environment properties.
   * @param {number} status - 0 for disable and 1 for enable.
   */
  setEnvPropertyStatus: function (status) {
    let selectedPropertyIds = jQ('#id_properties_container input[name="id"]:checked').filter(function () {
      if (status === 0) {
        if (! jQ(this).next('a').hasClass('line-through')) {
          return this;
        }
      } else {
        if (jQ(this).next('a').hasClass('line-through')) {
          return this;
        }
      }
    }).map(function () {
      return jQ(this).val();
    }).get();

    if (selectedPropertyIds.length === 0) {
      return;
    }

    postRequest({
      url: MgtEnv.Property.URLs.set_property_status,
      data: {id: selectedPropertyIds, status: status},
      traditional: true,
      success: function (data) {
        data.property_ids.forEach(function (propertyId) {
          if (status === 0) {
            jQ('#id_property_name_' + propertyId).addClass('line-through');
          } else {
            jQ('#id_property_name_' + propertyId).removeClass('line-through');
          }
        });
      },
    });
  },
};

Nitrate.Management.Environment.PropertyValue = {
  /**
   * Add an environment property value.
   * @param {number} propertyId
   */
  add: function (propertyId) {
    let valueName = jQ('#id_value_name').val().trim();
    if (!valueName) {
      return;
    }

    if (!valueName.replace(/\040/g, '').replace(/%20/g, '').length) {
      showModal('Value name could not be blank or space.');
      return;
    }

    let valuesToAdd = valueName.split(',').filter(function (item) {
      let s = item.trim();
      if (s.length > 0) {
        return s;
      }
    });

    postHTMLRequest({
      url: MgtEnv.Property.URLs.add_property_value.replace('$id', propertyId),
      traditional: true,
      data: {value: valuesToAdd},
      container: jQ('#id_values_container'),
      callbackAfterFillIn: MgtEnv.PropertyValue.bindPropertyValueActions,
      forbiddenMessage: 'You are not allowed to change environment property status.',
    });
  },

  /**
   * Edit an environment property value.
   * @param {number} propertyId
   * @param {number} valueId
   */
  edit: function (propertyId, valueId) {
    let newValueName = prompt('New value name', jQ('#id_value_' + valueId.toString()).html());
    if (! newValueName) {
      return;
    }

    postHTMLRequest({
      url: MgtEnv.Property.URL.edit_property_value.replace('$id', valueId.toString()),
      data: {value: newValueName},
      container: jQ('#id_values_container'),
      callbackAfterFillIn: MgtEnv.PropertyValue.bindPropertyValueActions,
      forbiddenMessage: 'You are not allowed to change environment property status.',
    });
  },

  /**
   * Disable an environment property value.
   * @param {number} status - 0 for disable and 1 for enable.
   */
  setStatus: function (status) {
    let selectedPropertyValues = jQ('#id_values_container input[name="id"]:checked').map(function () {
      return jQ(this).val();
    }).get();

    if (selectedPropertyValues.length === 0) {
      showModal('Please click the checkbox to choose values.');
      return;
    }

    postHTMLRequest({
      url: MgtEnv.Property.URLs.set_property_values_status,
      data: {status: status, id: selectedPropertyValues},
      traditional: true,
      container: jQ('#id_values_container'),
      callbackAfterFillIn: MgtEnv.PropertyValue.bindPropertyValueActions,
      forbiddenMessage: 'You are not allowed to change environment property status.',
    });
  },

  bindPropertyValueActions: function () {
    let propId = parseInt(jQ('.js-prop-value-action').data('param'));

    jQ('#property_values_form').on('submit', function () {
      // Disable form submit. Please press the Add button.
      return false;
    });

    const PropertyValue = MgtEnv.PropertyValue;

    jQ('#js-add-prop-value').on('click', function () {
      PropertyValue.add(propId);
    });

    jQ('#js-disable-prop-value').on('click', function () {
      PropertyValue.setStatus(0);
    });

    jQ('#js-enable-prop-value').on('click', function () {
      PropertyValue.setStatus(1);
    });

    jQ('.js-edit-prop-value').on('click', function () {
      let valueId = parseInt(jQ(this).data('param'));
      PropertyValue.edit(propId, valueId);
    });

    jQ('#property_values_form input[name=value_name]').focus();
  }
};
