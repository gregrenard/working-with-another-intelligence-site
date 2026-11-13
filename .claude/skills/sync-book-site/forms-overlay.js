// Deploy-time overlay, published as assets/forms.js by patch-forms.py (config: site-config.json).
// Design ships the three forms with a handler that only shows a success state and drops the data.
// This script listens for `submit` in the capture phase, before the page's own handler runs, and
// posts the fields to the Google Apps Script web app (source: forms-apps-script.gs), which appends
// a row to the tab named by `_form`. It never prevents the default handling, so the page still
// shows its own thank-you state. The form is told apart by its field names:
//   media            -> Press invite  (journalists and event organisers)
//   book_lang/format + company -> Reserve (pre-order)
//   anything else with an email -> Free chapter
(function () {
  var C = window.BOOK_FORMS || {};
  function tabFor(f) {
    var has = function (n) { return !!f.querySelector('[name="' + n + '"]'); };
    if (has('media')) return 'Press invite';
    if (has('book_lang') || has('company')) return 'Reserve';
    return has('email') ? 'Free chapter' : 'Other';
  }
  document.addEventListener('submit', function (e) {
    var f = e.target;
    if (!C.formEndpoint || !f || !f.querySelector || !f.querySelector('input[type=email]')) return;
    var body = new URLSearchParams(new FormData(f));
    body.append('_form', tabFor(f));
    body.append('_page', location.href.split('#')[0]);
    body.append('_lang', document.documentElement.lang || '');
    // Apps Script does not keep the order of posted fields: send it, so sheet columns follow the form.
    body.append('_fields', Array.prototype.map.call(f.elements, function (el) { return el.name; })
      .filter(function (n, i, a) { return n && a.indexOf(n) === i; }).join(','));
    try { fetch(C.formEndpoint, { method: 'POST', mode: 'no-cors', keepalive: true, body: body }).catch(function () {}); } catch (x) {}
  }, true);
})();
