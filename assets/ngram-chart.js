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

  /* ── CLUSTERMAP ── */
  window.renderClustermap = function (selector, jsonPath) {
    const container = document.querySelector(selector);
    if (!container) { console.warn('ngram-chart: not found:', selector); return; }

    fetch(jsonPath)
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(data => {
        const titles = data.titles;
        const matrix = data.matrix;
        const n      = titles.length;
        const dend   = data.dendrogram || null;

        const W        = container.clientWidth || 680;
        const DEND_W   = dend ? 120 : 4;  // left dendrogram strip
        const DEND_H   = dend ? 120 : 4;  // top dendrogram strip
        const CB_TOTAL = 55;               // colorbar + axis labels
        const heatSize = W - DEND_W - CB_TOTAL - 4;
        const cellSize = heatSize / n;
        const svgH     = DEND_H + heatSize + 4;

        /* RdBu_r: low=-0.3 → blue, high=1.0 → red.
           d3.interpolateRdBu(0)=red, (1)=blue, so use (1-t) to get the reversed scheme. */
        const vmin = -0.3, vmax = 1.0;
        const colorFn = v => {
          const t = Math.max(0, Math.min(1, (v - vmin) / (vmax - vmin)));
          return d3.interpolateRdBu(1 - t);
        };

        const svg = d3.select(container).append('svg')
          .attr('width', W).attr('height', svgH);

        /* g is anchored at the top-left corner of the heatmap */
        const g = svg.append('g')
          .attr('transform', `translate(${DEND_W},${DEND_H})`);

        const tip = getTip();

        /* heatmap cells */
        matrix.forEach((row, i) => {
          row.forEach((val, j) => {
            g.append('rect')
              .attr('x', j * cellSize).attr('y', i * cellSize)
              .attr('width', cellSize + 0.5).attr('height', cellSize + 0.5)
              .attr('fill', colorFn(val))
              .on('mouseenter', function (ev) {
                tip.html(
                  `<div style="color:#9ca3af;font-size:0.65rem">${titles[i]}</div>` +
                  `<div style="color:#9ca3af;font-size:0.65rem">${titles[j]}</div>` +
                  `<div>r = ${val.toFixed(3)}</div>`
                ).style('opacity', 1);
              })
              .on('mousemove', function (ev) {
                tip.style('left', (ev.clientX + 14) + 'px').style('top', (ev.clientY - 32) + 'px');
              })
              .on('mouseleave', function () { tip.style('opacity', 0); });
          });
        });

        /* dendrograms */
        if (dend) {
          const maxD = dend.max_depth;
          /* sqrt scale spreads shallow branches (which dominate) across visible space */
          const depthPx = (d, stripSize) => stripSize * Math.sqrt(d / maxD);

          /* left dendrogram (row tree) — drawn to the left of the heatmap */
          const leftG = g.append('g').attr('transform', `translate(${-DEND_W},0)`);
          dend.icoord.forEach((ic, idx) => {
            const dc = dend.dcoord[idx];
            /* dc=0 → leaf → right edge (x=DEND_W); dc=maxD → root → left edge (x=0) */
            const pts = ic.map((v, k) => [DEND_W - depthPx(dc[k], DEND_W), v * cellSize / 10]);
            leftG.append('path')
              .attr('d', `M${pts[0]}L${pts[1]}L${pts[2]}L${pts[3]}`)
              .attr('fill', 'none').attr('stroke', '#9ca3af').attr('stroke-width', 0.8);
          });

          /* top dendrogram (column tree) — drawn above the heatmap */
          const topG = g.append('g').attr('transform', `translate(0,${-DEND_H})`);
          dend.icoord.forEach((ic, idx) => {
            const dc = dend.dcoord[idx];
            /* dc=0 → leaf → bottom (y=DEND_H); dc=maxD → root → top (y=0) */
            const pts = ic.map((v, k) => [v * cellSize / 10, DEND_H - depthPx(dc[k], DEND_H)]);
            topG.append('path')
              .attr('d', `M${pts[0]}L${pts[1]}L${pts[2]}L${pts[3]}`)
              .attr('fill', 'none').attr('stroke', '#9ca3af').attr('stroke-width', 0.8);
          });
        }

        /* colorbar — bottom=vmin=blue, top=vmax=red (matches RdBu_r) */
        const cbX = heatSize + 8, cbW = 10, cbH = Math.min(200, heatSize * 0.4);
        const cbY = (heatSize - cbH) / 2;
        const cbSteps = 60;
        for (let k = 0; k < cbSteps; k++) {
          const t = k / (cbSteps - 1);
          /* k=0 → y=cbY+cbH (bottom=vmin=blue), k=cbSteps-1 → y=cbY (top=vmax=red) */
          g.append('rect')
            .attr('x', cbX).attr('y', cbY + (1 - t) * cbH - 0.5)
            .attr('width', cbW).attr('height', cbH / cbSteps + 1)
            .attr('fill', d3.interpolateRdBu(1 - t));
        }
        const cbScale = d3.scaleLinear().domain([vmin, vmax]).range([cbH, 0]);
        g.append('g')
          .attr('transform', `translate(${cbX + cbW},${cbY})`)
          .call(d3.axisRight(cbScale).ticks(5).tickSize(3))
          .call(ax => ax.select('.domain').attr('stroke', '#dde1ea'))
          .call(ax => ax.selectAll('line').attr('stroke', '#dde1ea'))
          .call(ax => ax.selectAll('text')
            .style('font-family', MONO).style('font-size', '0.6rem').attr('fill', MUTED));
      })
      .catch(err => {
        container.innerHTML =
          `<p style="font-family:${MONO};font-size:0.75rem;color:${MUTED};padding:1rem 0">` +
          `Chart unavailable (${err.message})</p>`;
      });
  };

  /* ── CLUSTER TRAJECTORY ── */
  window.renderClusterTrajectory = function (selector, jsonPath) {
    const container = document.querySelector(selector);
    if (!container) { console.warn('ngram-chart: not found:', selector); return; }

    fetch(jsonPath)
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(data => {
        const keys  = Object.keys(data.series);
        const years = data.years;
        const n     = keys.length;

        /* compute mean across all series at each year */
        const avgVals = years.map((_, i) => {
          const vals = keys.map(k => data.series[k][i]).filter(v => isFinite(v));
          return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : NaN;
        });

        function redraw() {
          container.innerHTML = '';
          const W           = container.clientWidth || 680;
          const innerWidth  = W - MARGIN.left - MARGIN.right;
          const innerHeight = HEIGHT - MARGIN.top - MARGIN.bottom;

          const svg = d3.select(container).append('svg').attr('width', W).attr('height', HEIGHT);
          const g   = svg.append('g').attr('transform', `translate(${MARGIN.left},${MARGIN.top})`);

          const xScale = d3.scaleLinear().domain(d3.extent(years)).range([0, innerWidth]);
          const yScale = d3.scaleLinear().domain([0, 1.05]).range([innerHeight, 0]);

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

          g.append('g').call(
            d3.axisLeft(yScale).ticks(5).tickSize(-innerWidth).tickFormat('')
          ).call(ax => ax.select('.domain').remove())
           .call(ax => ax.selectAll('line').attr('stroke', '#dde1ea').attr('stroke-dasharray', '2 3'));

          g.append('text')
            .attr('transform', 'rotate(-90)').attr('x', -innerHeight / 2).attr('y', -MARGIN.left + 14)
            .attr('text-anchor', 'middle')
            .style('font-family', MONO).style('font-size', '0.65rem').attr('fill', MUTED)
            .text('Normalized frequency (0–1)');

          g.append('text')
            .attr('x', innerWidth / 2).attr('y', innerHeight + MARGIN.bottom - 4)
            .attr('text-anchor', 'middle')
            .style('font-family', MONO).style('font-size', '0.65rem').attr('fill', MUTED)
            .text('Years after publication');

          const lineGen = d3.line()
            .defined(d => isFinite(d))
            .x((_, i) => xScale(years[i])).y(d => yScale(d))
            .curve(d3.curveMonotoneX);

          const tip = getTip();

          /* thin individual lines */
          keys.forEach(key => {
            const grp = g.append('g');

            /* visible line */
            grp.append('path').datum(data.series[key])
              .attr('class', 'traj-line')
              .attr('fill', 'none')
              .attr('stroke', '#2563eb').attr('stroke-width', 0.7).attr('opacity', 0.18)
              .attr('d', lineGen);

            /* invisible fat hit area */
            grp.append('path').datum(data.series[key])
              .attr('fill', 'none').attr('stroke', 'transparent').attr('stroke-width', 8)
              .attr('d', lineGen)
              .style('cursor', 'crosshair')
              .on('mouseover', function () {
                grp.select('.traj-line').attr('stroke', '#dc2626').attr('stroke-width', 2).attr('opacity', 0.9);
                tip.html(key).style('opacity', 1);
              })
              .on('mousemove', function (ev) {
                tip.style('left', (ev.clientX + 14) + 'px').style('top', (ev.clientY - 28) + 'px');
              })
              .on('mouseout', function () {
                grp.select('.traj-line').attr('stroke', '#2563eb').attr('stroke-width', 0.7).attr('opacity', 0.18);
                tip.style('opacity', 0);
              });
          });

          /* thick average line */
          g.append('path').datum(avgVals)
            .attr('fill', 'none')
            .attr('stroke', '#1e3a5f').attr('stroke-width', 2.5).attr('opacity', 0.95)
            .attr('d', lineGen);

          /* label */
          g.append('text')
            .attr('x', innerWidth - 4).attr('y', 12)
            .attr('text-anchor', 'end')
            .style('font-family', MONO).style('font-size', '0.65rem').attr('fill', MUTED)
            .text(`n = ${n} novels`);
        }

        redraw();
        new ResizeObserver(redraw).observe(container);
      })
      .catch(err => {
        container.innerHTML =
          `<p style="font-family:${MONO};font-size:0.75rem;color:${MUTED};padding:1rem 0">` +
          `Chart unavailable (${err.message})</p>`;
      });
  };

  /* ── GENRE LINES ── */
  window.renderGenreLines = function (selector, jsonPath) {
    const container = document.querySelector(selector);
    if (!container) { console.warn('ngram-chart: not found:', selector); return; }

    fetch(jsonPath)
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(data => {
        const genres     = Object.keys(data.series);
        const years      = data.years;
        const colorScale = d3.scaleOrdinal().domain(genres).range(CAT_COLORS);
        const tip        = getTip();
        const LEG_W      = 170;
        const LM         = { top: 16, right: LEG_W + 16, bottom: 48, left: 64 };

        function redraw() {
          container.innerHTML = '';
          const W           = container.clientWidth || 720;
          const innerWidth  = W - LM.left - LM.right;
          const innerHeight = HEIGHT - LM.top - LM.bottom;

          const svg = d3.select(container).append('svg').attr('width', W).attr('height', HEIGHT);
          const g   = svg.append('g').attr('transform', `translate(${LM.left},${LM.top})`);

          const xScale = d3.scaleLinear().domain(d3.extent(years)).range([0, innerWidth]);
          const allVals = genres.flatMap(genre => data.series[genre].filter(v => v != null && isFinite(v)));
          const yMax    = (d3.max(allVals) || 1) * 1.08;
          const yScale  = d3.scaleLinear().domain([0, yMax]).range([innerHeight, 0]);

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

          g.append('g').call(d3.axisLeft(yScale).ticks(5).tickSize(-innerWidth).tickFormat(''))
            .call(ax => ax.select('.domain').remove())
            .call(ax => ax.selectAll('line').attr('stroke', '#dde1ea').attr('stroke-dasharray', '2 3'));

          /* baseline (Analysis 2) */
          if (data.baseline != null) {
            g.append('line')
              .attr('x1', 0).attr('x2', innerWidth)
              .attr('y1', yScale(data.baseline)).attr('y2', yScale(data.baseline))
              .attr('stroke', '#111827').attr('stroke-width', 0.9)
              .attr('stroke-dasharray', '4 4').attr('opacity', 0.35);
          }

          /* axis labels */
          g.append('text')
            .attr('x', innerWidth / 2).attr('y', innerHeight + LM.bottom - 6)
            .attr('text-anchor', 'middle')
            .style('font-family', MONO).style('font-size', '0.65rem').attr('fill', MUTED)
            .text(data.xLabel || 'Year');

          g.append('text')
            .attr('transform', 'rotate(-90)').attr('x', -innerHeight / 2).attr('y', -LM.left + 14)
            .attr('text-anchor', 'middle')
            .style('font-family', MONO).style('font-size', '0.65rem').attr('fill', MUTED)
            .text(data.yLabel || 'Normalized frequency');

          const lineGen = d3.line()
            .defined(d => d != null && isFinite(d))
            .x((_, i) => xScale(years[i])).y(d => yScale(d))
            .curve(d3.curveMonotoneX);

          /* lines + hit areas */
          const lineGroups = {};
          genres.forEach(genre => {
            const grp = g.append('g');
            lineGroups[genre] = grp;

            grp.append('path').datum(data.series[genre])
              .attr('class', 'genre-line')
              .attr('fill', 'none')
              .attr('stroke', colorScale(genre)).attr('stroke-width', 1.8).attr('opacity', 0.75)
              .attr('d', lineGen);

            grp.append('path').datum(data.series[genre])
              .attr('fill', 'none').attr('stroke', 'transparent').attr('stroke-width', 10)
              .attr('d', lineGen).style('cursor', 'pointer')
              .on('mouseover', function () {
                genres.forEach(gk => lineGroups[gk].select('.genre-line')
                  .attr('opacity', gk === genre ? 1 : 0.08)
                  .attr('stroke-width', gk === genre ? 2.6 : 1));
                const n = data.counts ? data.counts[genre] : '';
                tip.html(`<strong>${genre}</strong>${n ? `<br>n\u202f=\u202f${n}` : ''}`).style('opacity', 1);
              })
              .on('mousemove', function (ev) {
                tip.style('left', (ev.clientX + 14) + 'px').style('top', (ev.clientY - 28) + 'px');
              })
              .on('mouseout', function () {
                genres.forEach(gk => lineGroups[gk].select('.genre-line')
                  .attr('opacity', 0.75).attr('stroke-width', 1.8));
                tip.style('opacity', 0);
              });
          });

          /* legend */
          const leg = svg.append('g')
            .attr('transform', `translate(${LM.left + innerWidth + 20},${LM.top})`);
          genres.forEach((genre, i) => {
            const row = leg.append('g').attr('transform', `translate(0,${i * 18})`).style('cursor', 'pointer');
            row.append('rect').attr('width', 14).attr('height', 3).attr('y', 5).attr('rx', 1)
              .attr('fill', colorScale(genre));
            row.append('text').attr('x', 20).attr('y', 11)
              .style('font-family', MONO).style('font-size', '0.62rem').attr('fill', MUTED)
              .text(`${genre}${data.counts ? ` (${data.counts[genre]})` : ''}`);
            row
              .on('mouseover', function () {
                genres.forEach(gk => lineGroups[gk].select('.genre-line')
                  .attr('opacity', gk === genre ? 1 : 0.08)
                  .attr('stroke-width', gk === genre ? 2.6 : 1));
                row.select('text').attr('fill', '#111827');
              })
              .on('mouseout', function () {
                genres.forEach(gk => lineGroups[gk].select('.genre-line')
                  .attr('opacity', 0.75).attr('stroke-width', 1.8));
                row.select('text').attr('fill', MUTED);
              });
          });
        }

        redraw();
        new ResizeObserver(redraw).observe(container);
      })
      .catch(err => {
        container.innerHTML =
          `<p style="font-family:${MONO};font-size:0.75rem;color:${MUTED};padding:1rem 0">` +
          `Chart unavailable (${err.message})</p>`;
      });
  };

  /* ── PAIR TRAJECTORIES — 3-panel grid, each panel = two novel lines ── */
  window.renderPairTrajectories = function (selector, jsonPath) {
    const container = document.querySelector(selector);
    if (!container) { console.warn('ngram-chart: not found:', selector); return; }

    fetch(jsonPath)
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(data => {
        const { years, pairs, series } = data;
        const PANEL_H   = 240;
        const PM        = { top: 28, right: 16, bottom: 36, left: 52 };
        const PAIR_COLORS = ['#2563eb', '#dc2626'];
        const tip = getTip();

        const grid = d3.select(container).append('div')
          .style('display', 'grid')
          .style('grid-template-columns', 'repeat(auto-fit, minmax(240px, 1fr))')
          .style('gap', '1.2rem');

        function drawPanel(parentEl, pair) {
          const panelNode = parentEl.node();

          function redraw() {
            panelNode.innerHTML = '';
            const W          = panelNode.clientWidth || 300;
            const innerW     = W - PM.left - PM.right;
            const innerH     = PANEL_H - PM.top - PM.bottom;

            const svg = d3.select(panelNode).append('svg').attr('width', W).attr('height', PANEL_H);
            const g   = svg.append('g').attr('transform', `translate(${PM.left},${PM.top})`);

            const xScale = d3.scaleLinear().domain(d3.extent(years)).range([0, innerW]);
            const titles = [pair.a, pair.b];
            const allVals = titles.flatMap(t => series[t] || []).filter(isFinite);
            const yScale  = d3.scaleLinear()
              .domain([0, (d3.max(allVals) || 1) * 1.08])
              .range([innerH, 0]).nice();

            /* panel header — book names + r value */
            titles.forEach((title, ti) => {
              const short = title.length > 28 ? title.slice(0, 26) + '…' : title;
              svg.append('text')
                .attr('x', PM.left).attr('y', 11 + ti * 13)
                .style('font-family', MONO).style('font-size', '0.62rem').attr('fill', PAIR_COLORS[ti])
                .text(short);
            });
            svg.append('text')
              .attr('x', W - PM.right).attr('y', 11)
              .attr('text-anchor', 'end')
              .style('font-family', MONO).style('font-size', '0.62rem').attr('fill', MUTED)
              .text(`r\u202f=\u202f${pair.r.toFixed(3)}`);

            /* axes */
            g.append('g').attr('transform', `translate(0,${innerH})`)
              .call(d3.axisBottom(xScale).tickFormat(d3.format('d'))
                                          .ticks(Math.min(6, Math.floor(innerW / 60))))
              .call(ax => ax.select('.domain').attr('stroke', '#dde1ea'))
              .call(ax => ax.selectAll('line').attr('stroke', '#dde1ea'))
              .call(ax => ax.selectAll('text').style('font-family', MONO)
                                               .style('font-size', '0.6rem').attr('fill', MUTED));

            g.append('g').call(d3.axisLeft(yScale).ticks(4))
              .call(ax => ax.select('.domain').remove())
              .call(ax => ax.selectAll('line').attr('stroke', '#dde1ea'))
              .call(ax => ax.selectAll('text').style('font-family', MONO)
                                               .style('font-size', '0.6rem').attr('fill', MUTED));

            g.append('g').call(
              d3.axisLeft(yScale).ticks(4).tickSize(-innerW).tickFormat('')
            ).call(ax => ax.select('.domain').remove())
             .call(ax => ax.selectAll('line').attr('stroke', '#dde1ea').attr('stroke-dasharray', '2 3'));

            const lineGen = d3.line()
              .defined(d => isFinite(d))
              .x((_, i) => xScale(years[i])).y(d => yScale(d))
              .curve(d3.curveMonotoneX);

            titles.forEach((title, ti) => {
              const vals = series[title];
              if (!vals) return;
              const color = PAIR_COLORS[ti];
              const grp   = g.append('g');

              grp.append('path').datum(vals)
                .attr('class', 'pair-line')
                .attr('fill', 'none').attr('stroke', color)
                .attr('stroke-width', 1.6).attr('opacity', 0.8)
                .attr('d', lineGen);

              grp.append('path').datum(vals)
                .attr('fill', 'none').attr('stroke', 'transparent').attr('stroke-width', 10)
                .attr('d', lineGen).style('cursor', 'crosshair')
                .on('mouseover', function () {
                  grp.select('.pair-line').attr('stroke-width', 2.6).attr('opacity', 1);
                  tip.html(`<span style="color:${color}">■</span> ${title}`).style('opacity', 1);
                })
                .on('mousemove', function (ev) {
                  tip.style('left', (ev.clientX + 14) + 'px').style('top', (ev.clientY - 28) + 'px');
                })
                .on('mouseout', function () {
                  grp.select('.pair-line').attr('stroke-width', 1.6).attr('opacity', 0.8);
                  tip.style('opacity', 0);
                });
            });

          }

          redraw();
          new ResizeObserver(redraw).observe(panelNode);
        }

        pairs.forEach(pair => {
          const cell = grid.append('div');
          drawPanel(cell, pair);
        });
      })
      .catch(err => {
        container.innerHTML =
          `<p style="font-family:${MONO};font-size:0.75rem;color:${MUTED};padding:1rem 0">` +
          `Chart unavailable (${err.message})</p>`;
      });
  };

  /* ── PAIRS TABLE ── */
  window.renderPairsTable = function (selector, jsonPath, mode /* 'top' | 'bottom' */) {
    const container = document.querySelector(selector);
    if (!container) { console.warn('ngram-chart: not found:', selector); return; }

    fetch(jsonPath)
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(data => {
        const titles = data.titles;
        const matrix = data.matrix;
        const n = titles.length;

        /* Build all unique pairs */
        const pairs = [];
        for (let i = 0; i < n; i++) {
          for (let j = i + 1; j < n; j++) {
            pairs.push({ a: titles[i], b: titles[j], r: matrix[i][j] });
          }
        }
        pairs.sort((x, y) => y.r - x.r);

        const rows = mode === 'bottom'
          ? pairs.slice(-15).reverse()
          : pairs.slice(0, 15);

        /* Color scale: r → hue (mirrors clustermap RdBu_r) */
        const vmin = -0.3, vmax = 1.0;
        const cellColor = r => {
          const t = Math.max(0, Math.min(1, (r - vmin) / (vmax - vmin)));
          return d3.interpolateRdBu(1 - t);
        };

        /* Build table with D3 */
        const wrap = d3.select(container).append('div')
          .style('overflow-x', 'auto');

        const table = wrap.append('table')
          .style('width', '100%')
          .style('border-collapse', 'collapse')
          .style('font-family', MONO)
          .style('font-size', '0.72rem');

        /* Header */
        table.append('thead').append('tr')
          .selectAll('th')
          .data(['Novel A', 'Novel B', 'Pearson r'])
          .join('th')
          .style('background', '#1e3a5f')
          .style('color', '#ffffff')
          .style('font-weight', '600')
          .style('padding', '0.55rem 0.9rem')
          .style('text-align', 'left')
          .style('border', '1px solid #dde1ea')
          .text(d => d);

        /* Body */
        const tbody = table.append('tbody');
        rows.forEach((row, i) => {
          const tr = tbody.append('tr')
            .style('background', i % 2 === 0 ? '#ffffff' : '#f1f5f9');

          [row.a, row.b].forEach(txt => {
            tr.append('td')
              .style('padding', '0.45rem 0.9rem')
              .style('border', '1px solid #dde1ea')
              .style('color', '#374151')
              .text(txt);
          });

          /* r cell with inline color swatch */
          const rCell = tr.append('td')
            .style('padding', '0.45rem 0.9rem')
            .style('border', '1px solid #dde1ea')
            .style('white-space', 'nowrap');

          rCell.append('span')
            .style('display', 'inline-block')
            .style('width', '10px')
            .style('height', '10px')
            .style('border-radius', '2px')
            .style('background', cellColor(row.r))
            .style('margin-right', '0.45rem')
            .style('vertical-align', 'middle');

          rCell.append('span')
            .style('color', '#374151')
            .text(row.r.toFixed(3));
        });
      })
      .catch(err => {
        container.innerHTML =
          `<p style="font-family:${MONO};font-size:0.75rem;color:${MUTED};padding:1rem 0">` +
          `Table unavailable (${err.message})</p>`;
      });
  };

  /* ── AUTO-INIT — scans for data-chart attributes on DOMContentLoaded ── */
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-chart]').forEach(function (el) {
      const type = el.dataset.chart;
      const src  = el.dataset.src;
      if (!src) { console.warn('ngram-chart: missing data-src on', el); return; }
      if (!el.id) el.id = 'chart-' + Math.random().toString(36).slice(2);
      const sel = '#' + el.id;
      if (type === 'separate')    window.renderSeparate(sel, src);
      if (type === 'aggregate')   window.renderAggregate(sel, src);
      if (type === 'comparison')  window.renderComparison(sel, src);
      if (type === 'clustermap')          window.renderClustermap(sel, src);
      if (type === 'cluster-trajectory') window.renderClusterTrajectory(sel, src);
      if (type === 'genre-lines')        window.renderGenreLines(sel, src);
      if (type === 'pairs-table')         window.renderPairsTable(sel, src, el.dataset.mode || 'top');
      if (type === 'pair-trajectories')  window.renderPairTrajectories(sel, src);
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
