// Tiny local bar-chart helper. No network, no dynamic code loading.
function drawBars(canvasId, values) {
  var ctx = document.getElementById(canvasId).getContext('2d');
  var max = Math.max.apply(null, values);
  values.forEach(function (v, i) {
    ctx.fillRect(10 + i * 40, 280 - (v / max) * 260, 30, (v / max) * 260);
  });
}
