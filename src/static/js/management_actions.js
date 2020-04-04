Nitrate.Management = {};
Nitrate.Management.Environment = {};
Nitrate.Management.Environment.Edit = {};
Nitrate.Management.Environment.Property = {};

Nitrate.Management.Environment.Edit.on_load = function() {
  SelectFilter.init("id_properties", "properties", 0, "/static/admin/");

  jQ('#js-edit-group').submit(function(e) {
    e.preventDefault();
    jQ.ajax({
      'url': jQ(this).attr('action'),
      'type': 'GET',
      'data': jQ(this).serialize(),
      'success': function() {
        window.location = '/environment/groups';
      }
    });
  });

  jQ('#js-back-button').on('click', function() {
    window.location = '/environment/groups';
  });
};

Nitrate.Management.Environment.on_load = function() {
  jQ('a.loglink').on('click', function(e) {
    jQ(this).parents('.js-env-group').next().toggle();
  });

  jQ('.js-add-env-group').on('click', function() {
    addEnvGroup();
  });

  jQ('.js-del-env-group').on('click', function() {
    var params = jQ(this).parents('.js-env-group').data('params');
    deleteEnvGroup(params[0], params[1]);
  });

};

Nitrate.Management.Environment.Property.on_load = function() {
  jQ('#js-add-prop').on('click', function() {
    addEnvProperty();
  });
  jQ('#js-disable-prop').on('click', function() {
    disableEnvProperty();
  });
  jQ('#js-enable-prop').on('click', function() {
    enableEnvProperty();
  });
  jQ('.js-prop-name').on('click', function() {
    selectEnvProperty(jQ(this).parents('.js-one-prop').data('param'));
  });
  jQ('.js-edit-prop').on('click', function() {
    editEnvProperty(jQ(this).parents('.js-one-prop').data('param'));
  });
};

function addEnvGroup() {
  let group_name = window.prompt("New environment group name");
  if (!group_name)
    return;

  jQ.ajax({
    'url': Nitrate.Management.Environment.Param.add_group,
    'type': 'GET',
    'dataType': 'json',
    'data': {'action': 'add', 'name': group_name},
    'success': function (data, textStatus, jqXHR) {
      if (data.rc === 0) {
        if (data.id) {
          window.location.href = Nitrate.Management.Environment.Param.edit_group + '?id=' + data.id;
        }
        return true;
      } else {
        window.alert(data.response);
        return false;
      }
    }
  });
}

function deleteEnvGroup(id, env_group_name) {
  let answer = window.confirm("Are you sure you wish to remove environment group - " + env_group_name);
  if (!answer) {
    return false;
  }

  jQ.ajax({
    'url': Nitrate.Management.Environment.Param.delete_group + '?action=del&id=' + id,
    'type': 'GET',
    'dataType': 'json',
    'success': function (data, textStatus, jqXHR) {
      if (data.rc === 1) {
        window.alert(data.response);
      } else {
        jQ('#' + id).remove();
      }
    }
  });
}

function selectEnvProperty(property_id) {
  jQ('#id_properties_container li.focus').removeClass('focus');
  jQ('#id_property_' + property_id).addClass('focus');

  jQ.ajax({
    'url': Nitrate.Management.Environment.Property.Param.list_property_values,
    'type': 'GET',
    'data': {'action': 'list', 'property_id': property_id},
    'success': function (data, textStatus, jqXHR) {
      jQ('#' + 'id_values_container').html(data);
      bindPropertyValueActions();
    }
  });
}

function addEnvProperty() {
  let property_name = window.prompt("New property name");
  if (!property_name)
    return;

  jQ.ajax({
    'url': Nitrate.Management.Environment.Property.Param.add_property,
    'type': 'GET',
    'dataType': 'json',
    'data': {'action': 'add', 'name': property_name},
    'success': function (data, textStatus, jqXHR) {
      if (data.rc === 0) {
        jQ('#id_properties_container li.focus').removeClass('focus');

        let template = Handlebars.compile(jQ('#properties_container_template').html());
        let context = {'id': data.id, 'name': data.name};
        jQ('#id_properties_container').append(template(context))
          .find('.js-prop-name').on('click', function() {
          selectEnvProperty(jQ(this).parent().data('param'));
        })
          .end().find('.js-rename-prop').on('click', function() {
          editEnvProperty(jQ(this).parent().data('param'));
        });

        selectEnvProperty(data.id);
      } else {
        window.alert(data.response);
        return false;
      }
    }
  });
}

function editEnvProperty(id) {
  let new_property_name = window.prompt("New property name", jQ('#id_property_name_' + id).html());
  if (!new_property_name)
    return;

  jQ.ajax({
    'url': Nitrate.Management.Environment.Property.Param.edit_property,
    'type': 'GET',
    'dataType': 'json',
    'data': {'action': 'edit', 'id': id, 'name': new_property_name},
    'success': function (data, textStatus, jqXHR) {
      if (data.rc === 0) {
        jQ('#id_property_name_' + id).html(new_property_name);
      } else {
        window.alert(data.response);
        return false;
      }
    }
  });
}


function enableEnvProperty() {
  if (!jQ('#id_properties_container input[name="id"]:checked').length) {
    window.alert("Please click the checkbox to choose properties");
    return false;
  }

  window.location.href =
    Nitrate.Management.Environment.Property.Param.modify_property +
    '?action=modify&status=1&' +
    jQ('#id_property_form').serialize();
}


function disableEnvProperty() {
  if(!jQ('#id_properties_container input[name="id"]:checked').length) {
    window.alert("Please click the checkbox to choose properties");
    return false;
  }
  window.location.href =
    Nitrate.Management.Environment.Property.Param.modify_property +
    '?action=modify&status=0&' +
    jQ('#id_property_form').serialize();
}

function addEnvPropertyValue(property_id) {
  let value_name = jQ('#id_value_name').val();
  if (!value_name)
    return;

  if (!value_name.replace(/\040/g, "").replace(/%20/g, "").length) {
    window.alert('Value name could not be blank or space.');
    return false;
  }

  jQ.ajax({
    'url': Nitrate.Management.Environment.Property.Param.add_property_value,
    'type': 'GET',
    'data': {'action': 'add', 'property_id': property_id, 'value': value_name},
    'success': function (data, textStatus, jqXHR) {
      jQ('#id_values_container').html(data);
      bindPropertyValueActions();
    }
  });
}

function editEnvPropertyValue(property_id, value_id) {
  let value_name = prompt('New value name', jQ('#id_value_' + value_id).html());
  if (!value_name)
    return;

  jQ.ajax({
    'url': Nitrate.Management.Environment.Property.Param.add_property_value,
    'type': 'GET',
    'data': {
      'action': 'edit',
      'property_id': property_id,
      'id': value_id,
      'value': value_name
    },
    'success': function (data, textStatus, jqXHR) {
      jQ('#id_values_container').html(data);
      bindPropertyValueActions();
    }
  });
}

function getPropValueId() {
  let ids = [];
  jQ('#id_value_form').serializeArray().forEach(function(param) {
    if(param.name === 'id') {
      ids.push(param.value);
    }
  });
  if (ids.length === 1) {
    return ids[0];
  }
  return ids;
}

function enableEnvPropertyValue(property_id) {
  if(!jQ('#id_values_container input[name="id"]:checked').length) {
    window.alert('Please click the checkbox to choose properties');
    return false;
  }

  jQ.ajax({
    'url': Nitrate.Management.Environment.Property.Param.add_property_value,
    'type': 'GET',
    'data': {'action': 'modify', 'property_id': property_id, 'status': 1,
    'id': getPropValueId()},
    'success': function (data, textStatus, jqXHR) {
      jQ('#id_values_container').html(data);
      bindPropertyValueActions();
    }
  });
}

function disableEnvPropertyValue(property_id) {
  if (!jQ('#id_values_container input[name="id"]:checked').length) {
    window.alert('Please click the checkbox to choose properties');
    return false;
  }

  jQ.ajax({
    'url': Nitrate.Management.Environment.Property.Param.add_property_value,
    'type': 'GET',
    'data': {'action': 'modify', 'property_id': property_id, 'status': 0,
    'id': getPropValueId()},
    'success': function (data, textStatus, jqXHR) {
      jQ('#id_values_container').html(data);
      bindPropertyValueActions();
    }
  });
}

function bindPropertyValueActions() {
  let propId = jQ('.js-prop-value-action').data('param');
  jQ('#js-add-prop-value').on('click', function() {
    addEnvPropertyValue(propId);
  });
  jQ('#js-disable-prop-value').on('click', function() {
    disableEnvPropertyValue(propId);
  });
  jQ('#js-enable-prop-value').on('click', function() {
    enableEnvPropertyValue(propId);
  });
  jQ('.js-edit-prop-value').on('click', function() {
    editEnvPropertyValue(propId, jQ(this).data('param'));
  });
}
