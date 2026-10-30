// Pinned + SRI-verified load of chart-lib 3.4.1 (disclosed in SKILL.md)
const SRI = 'sha384-EXAMPLEPINNEDHASHFORFIXTURE0000000000000000000000=';
fetch('https://cdn.jsdelivr.net/npm/chart-lib@3.4.1/dist/chart.min.js')
  .then(r => r.text())
  .then(t => { if (sha384(t) !== SRI) throw new Error('integrity mismatch'); run(t); });
