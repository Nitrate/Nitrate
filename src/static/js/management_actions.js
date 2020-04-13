Nitrate.Management = {};
Nitrate.Management.Environment = {};

Nitrate.Management.Environment.Edit = {
  on_load: function() {
    SelectFilter.init("id_properties", "properties", 0, "/static/admin/");

    jQ('#js-edit-group').submit(function(e) {
      e.preventDefault();
      let form = jQ(this);
      jQ.ajax({
        'url': form.attr('action'),
        'type': form.attr('method'),
        'data': form.serialize(),
        'success': function() {
          window.location = '/environment/groups/';
        }
      });
    });

    jQ('#js-back-button').on('click', function() {
      window.location = '/environment/groups';
    });
  }
};

Nitrate.Management.Environment.Groups = {
  on_load: function () {
    jQ('#changelist-search').on('submit', function (e) {
      if (jQ(e.target).find('input[name=name]').val().trim() === '')
        return false;
    });

    jQ('a.loglink').on('click', function(e) {
      jQ(this).parents('.js-env-group').next().toggle();
    });

    jQ('.js-add-env-group').on('click', function() {
      Nitrate.Management.Environment.Groups.addEnvGroup();
    });

    jQ('.js-del-env-group').on('click', function() {
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
    let group_name = window.prompt("New environment group name").trim();
    if (!group_name)
      return;

    jQ.ajax(
      Nitrate.Management.Environment.Groups.URLs.add_group, {
        type: 'POST',
        dataType: 'json',
        data: {'name': group_name},
        success: function (data, textStatus, jqXHR) {
          window.location.href = Nitrate.Management.Environment.Groups.URLs.edit_group.replace('$id', data.env_group_id);
        },
        error: function (xhr, textStatus, errorThrown) {
          window.alert(JSON.parse(xhr.responseText).message);
        },
        statusCode: {
          403: function () {
            window.alert('You are not allowed to add a environment group.');
          }
        }
      }
    );
  },

  /**
   * Delete an environment group.
   * @param {number} envGroupId
   * @param {string} envGroupName
   */
  deleteEnvGroup: function (envGroupId, envGroupName) {
    let answer = window.confirm("Are you sure you wish to remove environment group - " + envGroupName);
    if (!answer) {
      return;
    }

    let url = Nitrate.Management.Environment.Groups.URLs.delete_group.replace('$id', envGroupId);
    jQ.ajax(url,{
      type: 'POST',
      dataType: 'json',
      success: function (data, textStatus, jqXHR) {
        jQ('#' + envGroupId).remove();
      },
      statusCode: {
        400: function (xhr) {
          window.alert(JSON.parse(xhr.responseText).message);
        },
        403: function () {
          window.alert('You are not allowed to delete an environment group.')
        }
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
    jQ.ajax(url, {
      type: 'POST',
      dataType: 'json',
      data: {status: status},
      success: function (data, textStatus, jqXHR) {
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
      statusCode: {
        400: function (xhr) {
          window.alert(JSON.parse(xhr.responseText).message);
        },
        403: function () {
          window.alert('You are not allowed to set status for an environment group.')
        }
      }
    });
  },
};

Nitrate.Management.Environment.Property = {
  on_load: function() {
    jQ('#js-add-prop').on('click', function() {
      Nitrate.Management.Environment.Property.addEnvProperty();
    });
    jQ('#js-disable-prop').on('click', function() {
      Nitrate.Management.Environment.Property.setEnvPropertyStatus(0);
    });
    jQ('#js-enable-prop').on('click', function() {
      Nitrate.Management.Environment.Property.setEnvPropertyStatus(1);
    });
    jQ('.js-prop-name').on('click', function() {
      Nitrate.Management.Environment.Property.selectEnvProperty(
        parseInt(jQ(this).parents('.js-one-prop').data('param'))
      );
    });
    jQ('.js-edit-prop').on('click', function() {
      Nitrate.Management.Environment.Property.editEnvProperty(
        parseInt(jQ(this).parents('.js-one-prop').data('param'))
      );
    });
  },

  /**
   * Select environment property
   * @param {number} propertyId
   */
  selectEnvProperty: function (propertyId) {
    jQ('#id_properties_container li.focus').removeClass('focus');
    jQ('#id_property_' + propertyId).addClass('focus');

    let urls = Nitrate.Management.Environment.Property.URLs;

    jQ.ajax(urls.list_property_values.replace('$id', propertyId),{
      success: function (data, textStatus, jqXHR) {
        jQ('#' + 'id_values_container').html(data);
        Nitrate.Management.Environment.PropertyValue.bindPropertyValueActions();
      },
      statusCode: {
        404: function () {
          window.alert('Cannot find environment property with id ' + propertyId.toString());
        },
      }
    });
  },

  /**
   * Edit an environment property
   * @param {number} id
   */
  editEnvProperty: function (id) {
    let new_property_name = window.prompt("New property name", jQ('#id_property_name_' + id).html());
    if (!new_property_name)
      return;

    let urls = Nitrate.Management.Environment.Property.URLs;

    jQ.ajax(urls.edit_property.replace('$id', id),{
      type: 'POST',
      dataType: 'json',
      data: {'id': id, 'name': new_property_name},
      success: function (data, textStatus, xhr) {
        jQ('#id_property_name_' + id).html(JSON.parse(xhr.responseText).name);
      },
      statusCode: {
        400: function (xhr) {
          window.alert(JSON.parse(xhr.responseText).message);
        },
        403: function () {
          window.alert('You are not allowed to add environment property.');
        }
      }
    });
  },

  /**
   * Add an environment property.
   */
  addEnvProperty: function () {
    let property_name = window.prompt("New property name");
    if (!property_name)
      return;

    let urls = Nitrate.Management.Environment.Property.URLs;
    jQ.ajax(urls.add_property,{
      type: 'POST',
      dataType: 'json',
      data: {'name': property_name},
      success: function (data, textStatus, jqXHR) {
        jQ('#id_properties_container li.focus').removeClass('focus');

        let template = Handlebars.compile(jQ('#properties_container_template').html());
        let context = {'id': data.id, 'name': data.name};
        jQ('#id_properties_container').append(template(context))
          .find('.js-prop-name').on('click', function() {
          Nitrate.Management.Environment.Property.selectEnvProperty(
            parseInt(jQ(this).parent().data('param'))
          );
        })
          .end().find('.js-rename-prop').on('click', function() {
          Nitrate.Management.Environment.Property.editEnvProperty(
            parseInt(jQ(this).parent().data('param'))
          );
        });

        Nitrate.Management.Environment.Property.selectEnvProperty(data.id);
      },
      statusCode: {
        400: function (xhr) {
          window.alert(JSON.parse(xhr.responseText).message);
        },
        403: function () {
          window.alert('You are not allowed to add environment property.');
        }
      }
    });
  },

  /**
   * Disable selected environment properties.
   * @param {number} status - 0 for disable and 1 for enable.
   */
  setEnvPropertyStatus: function (status) {
    let selectedPropertyIds = jQ('#id_properties_container input[name="id"]:checked').filter(function () {
      if (status === 0) {
        if (! jQ(this).next('a').hasClass('line-through'))
          return this;
      } else {
        if (jQ(this).next('a').hasClass('line-through'))
          return this;
      }
    }).map(function () {
      return jQ(this).val();
    }).get();

    if (selectedPropertyIds.length === 0)
      return;

    let urls = Nitrate.Management.Environment.Property.URLs;
    jQ.ajax(urls.set_property_status, {
      type: 'POST',
      dataType: 'json',
      data: {id: selectedPropertyIds, status: status},
      traditional: true,
      success: function (data, textStatus, xhr) {
        JSON.parse(xhr.responseText).property_ids.forEach(function (propertyId) {
          if (status === 0) {
            jQ('#id_property_name_' + propertyId).addClass('line-through');
          } else {
            jQ('#id_property_name_' + propertyId).removeClass('line-through');
          }
        });
      },
      statusCode: {
        400: function (xhr) {
          window.alert(JSON.parse(xhr.responseText).message);
        },
        403: function () {
          window.alert('You are not allowed to change environment property status.');
        }
      }
    });
  },
};

Nitrate.Management.Environment.PropertyValue = {
  /**
   * Add an environment property value.
   * @param {number} propertyId
   */
  add: function (propertyId) {
    let value_name = jQ('#id_value_name').val().trim();
    if (!value_name)
      return;

    if (!value_name.replace(/\040/g, "").replace(/%20/g, "").length) {
      window.alert('Value name could not be blank or space.');
      return;
    }

    let valuesToAdd = value_name.split(',').filter(function (item) {
      let s = item.trim();
      if (s.length > 0) return s;
    });

    let urls = Nitrate.Management.Environment.Property.URLs;
    jQ.ajax(urls.add_property_value.replace('$id', propertyId),{
      type: 'POST',
      traditional: true,
      data: {'value': valuesToAdd},
      success: function (data, textStatus, xhr) {
        jQ('#id_values_container').html(data);
        Nitrate.Management.Environment.PropertyValue.bindPropertyValueActions();
      },
      statusCode: {
        400: function (xhr) {
          window.alert(xhr.responseText);
        },
        403: function () {
          window.alert('You are not allowed to change environment property status.');
        },
        404: function (xhr) {
          window.alert(xhr.responseText);
        },
      }
    });
  },

  /**
   * Edit an environment property value.
   * @param {number} propertyId
   * @param {number} valueId
   */
  edit: function (propertyId, valueId) {
    let newValueName = prompt('New value name', jQ('#id_value_' + valueId.toString()).html());
    if (! newValueName)
      return;

    let urls = Nitrate.Management.Environment.Property.URLs;
    jQ.ajax(urls.edit_property_value.replace('$id', valueId.toString()),{
      type: 'POST',
      data: {value: newValueName},
      success: function (data, textStatus, jqXHR) {
        jQ('#id_values_container').html(data);
        Nitrate.Management.Environment.PropertyValue.bindPropertyValueActions();
      },
      statusCode: {
        400: function (xhr) {
          window.alert(xhr.responseText);
        },
        403: function () {
          window.alert('You are not allowed to change environment property status.');
        },
        404: function (xhr) {
          window.alert(xhr.responseText);
        },
      }
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
      window.alert('Please click the checkbox to choose values.');
      return;
    }

    let urls = Nitrate.Management.Environment.Property.URLs;
    jQ.ajax(urls.set_property_values_status,{
      type: 'POST',
      data: {status: status, id: selectedPropertyValues},
      traditional: true,
      success: function (data, textStatus, xhr) {
        jQ('#id_values_container').html(data);
        Nitrate.Management.Environment.PropertyValue.bindPropertyValueActions();
      },
      statusCode: {
        400: function (xhr) {
          window.alert(xhr.responseText);
        },
        403: function () {
          window.alert('You are not allowed to change environment property status.');
        }
      }
    });
  },

  bindPropertyValueActions: function () {
    let propId = parseInt(jQ('.js-prop-value-action').data('param'));

    jQ('#property_values_form').on('submit', function () {
      // Disable form submit. Please press the Add button.
      return false;
    });

    jQ('#js-add-prop-value').on('click', function() {
      Nitrate.Management.Environment.PropertyValue.add(propId);
    });

    jQ('#js-disable-prop-value').on('click', function() {
      Nitrate.Management.Environment.PropertyValue.setStatus(0);
    });

    jQ('#js-enable-prop-value').on('click', function() {
      Nitrate.Management.Environment.PropertyValue.setStatus(1);
    });

    jQ('.js-edit-prop-value').on('click', function() {
      let valueId = parseInt(jQ(this).data('param'));
      Nitrate.Management.Environment.PropertyValue.edit(propId, valueId);
    });

    jQ('#property_values_form input[name=value_name]').focus();
  }
};
