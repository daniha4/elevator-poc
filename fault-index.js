/* fault-index.js — ES5 compatible */
var FAULT_JSON_URL = './data/fault_index.json';
var FAULTS = [];

function loadFaultIndex() {
  if (FAULTS.length > 0) { return Promise.resolve(); }
  return fetch(FAULT_JSON_URL, { cache: 'no-store' })
    .then(function(res) { return res.json(); })
    .then(function(data) { FAULTS = data; });
}

function searchFaults(manufacturer, controller, keyword) {
  var results = FAULTS;

  if (manufacturer) {
    results = results.filter(function(r) {
      return r.normalized_manufacturer === manufacturer;
    });
  }
  if (controller) {
    results = results.filter(function(r) {
      return r.normalized_controller === controller;
    });
  }
  if (keyword) {
    var kw = keyword.toLowerCase().trim();
    var HE = { 'קונה': 'kone', 'שינדלר': 'schindler', 'אוטיס': 'otis', 'טיקה': 'tke' };
    var search = HE[kw] || kw;

    var numVariants = [];
    if (/^\d+$/.test(search)) {
      var num = parseInt(search, 10);
      numVariants = [
        'code ' + num + ' ',
        'code ' + num + '|',
        String(num).padStart(2, '0'),
        String(num).padStart(3, '0'),
        String(num).padStart(4, '0'),
      ];
    }

    results = results.filter(function(r) {
      var hay = r.snippet.toLowerCase();
      var mfr = r.normalized_manufacturer.toLowerCase();
      var ctrl = r.normalized_controller.toLowerCase();
      if (hay.indexOf(search) !== -1) { return true; }
      if (mfr.indexOf(search) !== -1 || ctrl.indexOf(search) !== -1) { return true; }
      for (var i = 0; i < numVariants.length; i++) {
        if (hay.indexOf(numVariants[i]) !== -1) { return true; }
      }
      return false;
    });
  }

  var seen = {};
  var out = [];
  results.forEach(function(r) {
    var key = r.file + '|' + r.page;
    if (!seen[key]) {
      seen[key] = r;
      out.push(r);
    } else if (r.has_code === 'true' && seen[key].has_code !== 'true') {
      var idx = out.indexOf(seen[key]);
      if (idx !== -1) { out[idx] = r; }
      seen[key] = r;
    }
  });
  return out;
}
