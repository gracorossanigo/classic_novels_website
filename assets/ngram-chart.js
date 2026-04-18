/* ngram-chart.js — D3 chart renderer for Classic Novels
 *
 * Public API (load D3 before this script):
 *   renderSeparate(selector, jsonPath)   — per-language frequency lines + language toggles
 *   renderAggregate(selector, jsonPath)  — normalized aggregate fill+line + language toggles
 *   renderComparison(selector, jsonPath) — multi-title comparison lines + series toggles
 */
(function () {
  'use strict';

  /* ── CONSTANTS ── */
  const LANG_COLORS = {
    English: '#1f77b4', French: '#d62728', German: '#2ca02c',
    Italian: '#ff7f0e', Russian: '#9467bd', Spanish: '#8c564b',
  };
  const CAT_COLORS = [
    '#1f77b4','#d62728','#2ca02c','#ff7f0e',
    '#9467bd','#8c564b','#e377c2','#7f7f7f','#bcbd22','#17becf',
  ];
  const MARGIN   = { top: 16, right: 24, bottom: 40, left: 60 };
  const HEIGHT   = 340;
  const MONO     = "'DM Mono', monospace";
  const MUTED    = '#6b7280';

  /* ── TOOLTIP (shared singleton) ── */
  let _tip = null;
  function getTip() {
    if (_tip) return _tip;
    _tip = d3.select('body').append('div')
      .style('position', 'fixed').style('pointer-events', 'none')
      .style('opacity', 0).style('background', '#111827').style('color', '#f9fafb')
      .style('font-family', MONO).style('font-size', '0.72rem').style('line-height', '1.6')
      .style('padding', '0.45rem 0.75rem').style('border-radius', '4px')
      .style('max-width', '200px').style('z-index', '9999')
      .style('transition', 'opacity 0.15s');
    return _tip;
  }

  /* ── EVENT LINES ── */
  function addEventLines(g, events, xScale, innerHeight) {
    const tip = getTip();
    Object.entries(events).forEach(([yearStr, label]) => {
      const x = xScale(+yearStr);
      if (isNaN(x)) return;
      const grp = g.append('g');
      grp.append('line')
        .attr('class', 'evt-line')
        .attr('x1', x).attr('x2', x).attr('y1', 0).attr('y2', innerHeight)
        .attr('stroke', MUTED).attr('stroke-width', 1).attr('stroke-dasharray', '3 3')
        .style('opacity', 0.18).style('transition', 'opacity 0.18s');
      grp.append('rect')
        .attr('x', x - 10).attr('y', 0).attr('width', 20).attr('height', innerHeight)
        .attr('fill', 'transparent').style('cursor', 'default')
        .on('mouseenter', function () {
          grp.select('.evt-line').style('opacity', 0.85);
          tip.html(`<div style="color:#9ca3af;margin-bottom:3px">${yearStr}</div>${label.replace(/\n/g, '<br>')}`)
             .style('opacity', 1);
        })
        .on('mousemove', function (ev) {
          tip.style('left', (ev.clientX + 14) + 'px').style('top', (ev.clientY - 32) + 'px');
        })
        .on('mouseleave', function () {
          grp.select('.evt-line').style('opacity', 0.18);
          tip.style('opacity', 0);
        });
    });
  }

  /* ── TOGGLES ── */
  function addToggles(container, entries /* [{label, color}] */, activeSet, onToggle) {
    const wrap = document.createElement('div');
    wrap.className = 'chart-toggles';
    entries.forEach(({ label, color }) => {
      const btn = document.createElement('button');
      btn.className = 'chart-toggle-btn' + (activeSet.has(label) ? ' active' : '');
      btn.style.setProperty('--swatch-color', color);
      btn.innerHTML =
        `<span class="toggle-swatch" style="background:${color}"></span>${label}`;
      btn.addEventListener('click', () => {
        const nowActive = btn.classList.toggle('active');
        onToggle(label, nowActive);
      });
      
      wrap.appendChild(btn);
    });
    container.appendChild(wrap);
  }

  /* ── CORE DRAW — returns {label: d3Path} map ── */
  function draw(chartArea, data, { yLabel, scaleY, colorFn, fillFirst }) {
    const W           = chartArea.clientWidth || 680;
    const innerWidth  = W - MARGIN.left - MARGIN.right;
    const innerHeight = HEIGHT - MARGIN.top - MARGIN.bottom;

    const svg = d3.select(chartArea).append('svg').attr('width', W).attr('height', HEIGHT);
    const g   = svg.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);

    const entries = Object.entries(data.series);
    const years   = data.years;

    const xScale = d3.scaleLinear().domain(d3.extent(years)).range([0, innerWidth]);
    const yMax   = d3.max(entries.flatMap(([, v]) => v)) * scaleY;
    const yScale = d3.scaleLinear().domain([0, yMax * 1.06]).range([innerHeight, 0]).nice();

    /* axes */
    g.append('g').attr('transform', `translate(0,${innerHeight})`)
      .call(d3.axisBottom(xScale).tickFormat(d3.format('d'))
                                  .ticks(Math.min(8, Math.floor(innerWidth / 70))))
      .call(ax => ax.select('.domain').attr('stroke', '#dde1ea'))
      .call(ax => ax.selectAll('line').attr('stroke', '#dde1ea'))
      .call(ax => ax.selectAll('text').style('font-family', MONO)
                                       .style('font-size', '0.65rem').attr('fill', MUTED));

    g.append('g').call(d3.axisLeft(yScale).ticks(5))
      .call(ax => ax.select('.domain').remove())
      .call(ax => ax.selectAll('line').attr('stroke', '#dde1ea'))
      .call(ax => ax.selectAll('text').style('font-family', MONO)
                                       .style('font-size', '0.65rem').attr('fill', MUTED));

    /* gridlines */
    g.append('g').call(
      d3.axisLeft(yScale).ticks(5).tickSize(-innerWidth).tickFormat('')
    ).call(ax => ax.select('.domain').remove())
     .call(ax => ax.selectAll('line').attr('stroke', '#dde1ea').attr('stroke-dasharray', '2 3'));

    /* y label */
    g.append('text')
      .attr('transform', 'rotate(-90)').attr('x', -innerHeight / 2).attr('y', -MARGIN.left + 14)
      .attr('text-anchor', 'middle')
      .style('font-family', MONO).style('font-size', '0.65rem').attr('fill', MUTED)
      .text(yLabel);

    const lineGen = d3.line()
      .defined(d => !isNaN(d))
      .x((_, i) => xScale(years[i])).y(d => yScale(d * scaleY))
      .curve(d3.curveMonotoneX);

    /* area fill for aggregate */
    if (fillFirst && entries.length) {
      const areaGen = d3.area()
        .defined(d => !isNaN(d))
        .x((_, i) => xScale(years[i])).y0(innerHeight).y1(d => yScale(d * scaleY))
        .curve(d3.curveMonotoneX);
      g.append('path').datum(entries[0][1])
        .attr('fill', 'steelblue').attr('fill-opacity', 0.18).attr('d', areaGen);
    }

    /* series lines — return map for external opacity control */
    const lineMap = {};
    entries.forEach(([label, vals], i) => {
      lineMap[label] = g.append('path').datum(vals)
        .attr('fill', 'none').attr('stroke', colorFn(label, i))
        .attr('stroke-width', 1.8).attr('d', lineGen);
    });

    addEventLines(g, data.events, xScale, innerHeight);

    return lineMap;
  }

  /* ── AGGREGATE HELPER ── */
  function computeAggregate(series) {
    const parts = Object.values(series)
      .map(vals => { const m = Math.max(...vals); return m > 0 ? vals.map(v => v / m) : null; })
      .filter(Boolean);
    if (!parts.length) return [];
    return parts[0].map((_, i) => parts.reduce((s, p) => s + p[i], 0));
  }

  /* ── MOUNT: separate & comparison (toggle = opacity, no redraw) ── */
  function mountLineChart(selector, jsonPath, opts) {
    const container = document.querySelector(selector);
    if (!container) { console.warn('ngram-chart: not found:', selector); return; }

    fetch(jsonPath)
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(data => {
        const keys      = Object.keys(data.series);
        const activeSet = new Set(keys);
        let lineMap     = {};

        const chartArea = document.createElement('div');
        container.appendChild(chartArea);

        function redraw() {
          chartArea.innerHTML = '';
          lineMap = draw(chartArea, data, opts);
          keys.forEach(k => { if (!activeSet.has(k)) lineMap[k]?.style('opacity', 0.08); });
        }

        redraw();
        new ResizeObserver(redraw).observe(container);

        addToggles(container, keys.map((label, i) => ({ label, color: opts.colorFn(label, i) })),
          activeSet,
          (label, isActive) => {
            if (isActive) activeSet.add(label); else activeSet.delete(label);
            lineMap[label]?.style('opacity', isActive ? 1 : 0.08);
          });
      })
      .catch(err => {
        container.innerHTML =
          `<p style="font-family:${MONO};font-size:0.75rem;color:${MUTED};padding:1rem 0">` +
          `Chart unavailable (${err.message})</p>`;
      });
  }

  /* ── MOUNT: aggregate (toggle recomputes aggregate, needs redraw) ── */
  function mountAggregateChart(selector, jsonPath) {
    const container = document.querySelector(selector);
    if (!container) { console.warn('ngram-chart: not found:', selector); return; }

    fetch(jsonPath)
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(data => {
        const keys      = Object.keys(data.series);
        const activeSet = new Set(keys);

        const chartArea = document.createElement('div');
        container.appendChild(chartArea);

        function getAggData() {
          const filtered = Object.fromEntries(
            Object.entries(data.series).filter(([k]) => activeSet.has(k))
          );
          return { years: data.years, series: { Aggregate: computeAggregate(filtered) }, events: data.events };
        }

        const aggOpts = {
          yLabel: 'Normalized aggregate', scaleY: 1,
          colorFn: () => 'steelblue', fillFirst: true,
        };

        function redraw() {
          chartArea.innerHTML = '';
          draw(chartArea, getAggData(), aggOpts);
        }

        redraw();
        new ResizeObserver(redraw).observe(container);

        addToggles(container, keys.map(label => ({ label, color: LANG_COLORS[label] ?? '#888' })),
          activeSet,
          (label, isActive) => {
            if (isActive) activeSet.add(label); else activeSet.delete(label);
            redraw();
          });
      })
      .catch(err => {
        container.innerHTML =
          `<p style="font-family:${MONO};font-size:0.75rem;color:${MUTED};padding:1rem 0">` +
          `Chart unavailable (${err.message})</p>`;
      });
  }

  /* ── AUTO-INIT — scans for data-chart attributes on DOMContentLoaded ── */
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-chart]').forEach(function (el) {
      const type = el.dataset.chart;
      const src  = el.dataset.src;
      if (!src) { console.warn('ngram-chart: missing data-src on', el); return; }
      if (!el.id) el.id = 'chart-' + Math.random().toString(36).slice(2);
      const sel = '#' + el.id;
      if (type === 'separate')   window.renderSeparate(sel, src);
      if (type === 'aggregate')  window.renderAggregate(sel, src);
      if (type === 'comparison') window.renderComparison(sel, src);
    });
  });

  /* ── PUBLIC API ── */
  window.renderSeparate = (selector, jsonPath) =>
    mountLineChart(selector, jsonPath, {
      yLabel: 'Freq. per million words', scaleY: 1e6,
      colorFn: label => LANG_COLORS[label] ?? '#888', fillFirst: false,
    });

  window.renderAggregate = (selector, jsonPath) =>
    mountAggregateChart(selector, jsonPath);

  window.renderComparison = (selector, jsonPath) =>
    mountLineChart(selector, jsonPath, {
      yLabel: 'Freq. per million words', scaleY: 1e6,
      colorFn: (_, i) => CAT_COLORS[i % CAT_COLORS.length], fillFirst: false,
    });
})();
