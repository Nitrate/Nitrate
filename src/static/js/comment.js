/* eslint no-redeclare: "off" */
/* eslint no-unused-vars: "off" */

function removeComment(form, callback) {
  let parameters = Nitrate.Utils.formSerialize(form);

  postRequest({
    url: form.action,
    data: parameters,
    success: function (data) {
      updateCommentsCount(parameters.object_pk, false);
      callback(data);
    },
  });
}


function submitComment(container, parameters, callback) {
  // FIXME: Remove parameter container, it is not useless here.
  jQ(container).html(constructAjaxLoading());

  postRequest({
    url: '/comments/post/',
    data: parameters,
    success: function () {
      updateCommentsCount(parameters.object_pk, true);
      if (callback) {
        callback();
      }
    }
  });
}


function updateCommentsCount(caseId, increase) {
  let commentDiv = jQ('#' + caseId + '_case_comment_count');
  let countText = jQ('#' + caseId + '_comments_count');
  if (increase) {
    if (commentDiv.children().length === 1) {
      commentDiv.prepend('<img src="/static/images/comment.png" style="vertical-align: middle;">');
    }
    countText.text(' ' + (parseInt(countText.text()) + 1));
  } else {
    if (parseInt(countText.text(), 10) === 1) {
      commentDiv.html('<span id="' + caseId + '_comments_count"> 0</span>');
    } else {
      countText.text(' ' + (parseInt(commentDiv.text()) - 1));
    }
  }
}
