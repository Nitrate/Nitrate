/* global RIGHT_ARROW, DOWN_ARROW */

/**
 * @file Operation on the entity's detail expansion or collapse. This is for test case and the test
 *       case run particularly.
 * @author Chenxiong Qi
 */

/**
 * Base class for entity detail expansion and collapse. The entity is the case or case run particularly.
 *
 * @param {HTMLElement} originalElement
 *  the original element from which to trigger the expansion or collapse operation. This is usually
 *  an element having a CSS class .expandable inside a case TR row.
 * @class
 */
class DetailExpansion {
  constructor(originalElement) {
    this.originalElement = originalElement;
    this.entityRow = jQ(this.originalElement).parents('tr:first');
    this.detailRow = this.entityRow.next();
    this.caseId = window.parseInt(this.entityRow.find('input[name="case"]')[0].value);
    this.isDetailLoaded = this.detailRow.find('.ajax_loading').length === 0;
    this.colspan = this.entityRow.find('td').length;
    this.imgExpansionIcon = this.entityRow.find('img.blind_icon');
    if (this.imgExpansionIcon === undefined) {
      throw new Error('No expansion icon image is found in the case row.');
    }
  }

  /**
   * Load the entity detail. This method should be overriden in the subclass to load the specific
   * specific entity's detail, e.g. case or case run in particular.
   *
   * @param {Function} [callback]
   *  a function registered to a proper HTTP request function to be called after the detail content is
   *  filled into the container.
   */
  expand(callback) {
    throw new Error('This method should be called on subclass.');
  }

  /**
   * Toggle the entity's detail content.
   *
   * @param {Function} [callback] - passed to instance function expand.
   */
  toggle(callback) {
    this.detailRow.toggle();
    if (! this.isDetailLoaded) {
      this.expand(callback);
    }
    this.toggleExpandArrow();
  };

  /**
   * Change the expand/collapse icon accordingly.
   */
  toggleExpandArrow() {
    if (this.detailRow.is(':hidden')) {
      this.imgExpansionIcon.removeClass('collapse').addClass('expand').prop('src', RIGHT_ARROW);
    } else {
      this.imgExpansionIcon.removeClass('expand').addClass('collapse').prop('src', DOWN_ARROW);
    }
  }
}


/**
 * Toggle case detail
 *
 * @param {HTMLElement} originalElement - refer to the base class.
 * @param {boolean} [isReviewingCase=false] - whether to work on cases under review.
 * @class
 */
class CaseDetailExpansion extends DetailExpansion {
  constructor(originalElement, isReviewingCase) {
    super(originalElement);
    this.isReviewingCase = isReviewingCase === undefined ? false : isReviewingCase;
  }

  expand(callback) {
    let self = this
      , url = '/case/' + this.caseId.toString() +
      (this.isReviewingCase ? '/review-pane/' : '/readonly-pane/');

    sendHTMLRequest({
      url: url,
      container: this.detailRow,
      callbackAfterFillIn: callback || function () {
        // As of writing this class, different detail pane spans different
        // number of columns, which is not set dynamically. This could be a
        // workaround to fix that. Ideally, it should be set in the backend
        // somehow.
        self.detailRow.find('td:first').prop('colspan', self.colspan);
      }
    });
  }
}

class SimpleCaseRunDetailExpansion extends  DetailExpansion {
  constructor(originalElement) {
    super(originalElement);
    this.caseRunId = window.parseInt(this.entityRow.find('input[name="case_run"]')[0].value);
  }

  expand(callback) {
    sendHTMLRequest({
      url: '/case/' + this.caseId + '/caserun-simple-pane/',
      data: {case_run_id: this.caseRunId},
      container: this.detailRow
    })
  }
}


/**
 * Class managing test case run detail expansion.
 *
 * @param {HTMLElement} originalElement - refer to base class constructor.
 * @param {boolean} [showLoading=true] - whether to show the AJAX loading animation.
 * @class
 */
class CaseRunDetailExpansion extends SimpleCaseRunDetailExpansion {
  constructor(originalElement, showLoading) {
    super(originalElement);
    this.showLoadingAnimation = showLoading === undefined ? true : showLoading;
    // Workaround before renaming caseRow to a general name in base class.
    this.caseRunRow = this.entityRow;
    this.caseTextVersion = window.parseInt(this.entityRow.find('input[name="case_text_version"]')[0].value);
    this.atLastRow = this.detailRow.next().length === 0;
  }

  expand(callback) {
    if (this.showLoadingAnimation) {
      const td = document.createElement('td');
      td.colSpan = 14;
      td.appendChild(constructAjaxLoading());
      this.detailRow.html(td.outerHTML);
    }

    let self = this;

    sendHTMLRequest({
      url: '/case/' + this.caseId.toString() + '/caserun-detail-pane/',
      container: this.detailRow[0],
      callbackAfterFillIn: function () {
        Nitrate.TestRuns.Details.registerEventHandlersForCaseRunDetail(self);
      },
      data: {
        case_run_id: this.caseRunId,
        case_text_version: this.caseTextVersion
      }
    });
  }

  showCaseRunDetailAjaxLoading() {
    const td = document.createElement('td');
    td.colSpan = 14;
    td.appendChild(constructAjaxLoading());
    this.detailRow.html(td.outerHTML);
  }

  expandCaseRunDetail(caseRunRow) {
    let expansionIcon = caseRunRow.find('img.blind_icon.expand');
    if (expansionIcon.length > 0) {
      expansionIcon.trigger('click');
    }
  }

  expandNextCaseRunDetail() {
    // The first next is the case run's detail row
    let nextCaseRunRow = this.detailRow.next();
    this.expandCaseRunDetail(nextCaseRunRow);
  }

  collapseCaseRunDetail() {
    if (this.imgExpansionIcon.hasClass('collapse')) {
      this.imgExpansionIcon.trigger('click');
    }
  }
}

class PlanCaseRunsExpansion extends DetailExpansion {
  constructor(originalElement) {
    super(originalElement);
    this.caseRunPlanId = window.parseInt(this.entityRow[0].id);
  }

  expand(callback) {
    sendHTMLRequest({
      url: '/case/' + this.caseId.toString() + '/caserun-list-pane/',
      data: {plan_id: this.caseRunPlanId},
      container: this.detailRow[0],
      callbackAfterFillIn: callback,
    });
  }
}

/**
 * A simple event handler to toggle a specific test case detail.
 */
function caseDetailExpansionHandler() {
  new CaseDetailExpansion(this).toggle();
}
