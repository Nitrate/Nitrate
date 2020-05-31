function getWindowHeight() {
  let windowHeight = 0;
  if (typeof window.innerHeight === 'number') {
    windowHeight = window.innerHeight;
  } else {
    if (document.documentElement && document.documentElement.clientHeight) {
      windowHeight = document.documentElement.clientHeight;
    } else {
      if (document.body && document.body.clientHeight) {
        windowHeight = document.body.clientHeight;
      }
    }
  }
  return windowHeight;
}

function setFooter() {
  if (document.getElementById) {
    let windowHeight = getWindowHeight();
    if (windowHeight > 20) {
      let contentHeight = document.getElementById('content').offsetHeight;
      let footerElement = document.getElementById('footer');
      let footerHeight  = footerElement.offsetHeight;
      if (windowHeight - (contentHeight + footerHeight) >= 150) {
        footerElement.style.position = 'absolute';
        footerElement.style.bottom = 0 + 'px';
        footerElement.style.height = 20 + 'px';
      } else {
        footerElement.style.position = 'static';
      }
    }
  }
}

window.onload = function () {
  setFooter();
};

window.onresize = function () {
  setFooter();
};
