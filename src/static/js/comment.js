/* eslint no-redeclare: "off" */

function removeComment(form, callback) {
  let parameters = Nitrate.Utils.formSerialize(form);

  postRequest({
    url: form.action,
    data: parameters,
    success: function (data) {
      callback(data);
    },
  });
}


/**
 * Update comments count by increasing or decreasing the number.
 *
 * @param {number} caseId - the case id used to select specific elements to be updated.
 * @param {boolean} increase - increase or decrease the number.
 */
function updateCommentsCount(caseId, increase) {
  let commentDiv = jQ('#' + caseId.toString() + '_case_comment_count');
  let countText = jQ('#' + caseId.toString() + '_comments_count');
  if (increase) {
    if (commentDiv.children().length === 1) {
      commentDiv.prepend('<img src="/static/images/comment.png" style="vertical-align: middle;">');
    }
    countText.text(' ' + (parseInt(countText.text()) + 1));
  } else {
    if (parseInt(countText.text(), 10) === 1) {
      commentDiv.html('<span id="' + caseId.toString() + '_comments_count"> 0</span>');
    } else {
      countText.text(' ' + (parseInt(commentDiv.text()) - 1));
    }
  }
}
