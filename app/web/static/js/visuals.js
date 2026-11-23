/* Shared motion and visual helpers for the research platform. */
(function () {
  const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  window.APP_MOTION = !reduceMotion;
  window.CHART_OPTIONS = window.CHART_OPTIONS || {};
  const CHART_FONT_FAMILY = '"Segoe UI","Microsoft YaHei","PingFang SC",system-ui,sans-serif';
  const CRC_PALETTE = ['#2563eb', '#12a594', '#e8a33d', '#7c6ee6', '#df6478', '#2f9fda', '#ef8b42', '#49b77c', '#a77bf3', '#d35d5d', '#4e8df5', '#35b8b1'];
  window.CHART_FONT_FAMILY = CHART_FONT_FAMILY;
  window.CRC_PALETTE = CRC_PALETTE;

  function normalizedWeight(weight, minimum) {
    const words = { normal: 400, regular: 400, medium: 500, semibold: 600, bold: 700, bolder: 800 };
    const token = String(weight == null ? '' : weight).toLowerCase();
    const numeric = Number(weight);
    const value = Number.isFinite(numeric) ? numeric : (words[token] || 0);
    return Math.max(value, minimum);
  }

  function strengthenTextStyle(style, minSize, minWeight, color) {
    if (!style || typeof style !== 'object') return style;
    style.fontSize = Math.max(Number(style.fontSize) || 0, minSize);
    style.fontWeight = normalizedWeight(style.fontWeight, minWeight);
    if (color && !style.color) style.color = color;
    return style;
  }

  function strengthenAxis(axis) {
    if (!axis || typeof axis !== 'object') return;
    if (axis.axisLabel !== false) {
      axis.axisLabel = strengthenTextStyle(axis.axisLabel || {}, 14, 700, '#40566c');
      if (axis.type === 'category') {
        // Category names identify each bar/heatmap cell, so never let overlap detection silently drop them.
        if (axis.axisLabel.interval === undefined || axis.axisLabel.interval === 'auto') axis.axisLabel.interval = 0;
        if (axis.axisLabel.hideOverlap === undefined) axis.axisLabel.hideOverlap = false;
      } else if (axis.axisLabel.hideOverlap === undefined) {
        axis.axisLabel.hideOverlap = true;
      }
    }
    if (axis.name) axis.nameTextStyle = strengthenTextStyle(axis.nameTextStyle || {}, 15, 800, '#334e63');
  }

  function strengthenSeries(series) {
    if (!series || typeof series !== 'object') return;
    const denseHeatmap = series.type === 'heatmap';
    const labelSize = denseHeatmap ? 11 : 14;
    if (series.label !== false) series.label = strengthenTextStyle(series.label || {}, labelSize, denseHeatmap ? 700 : 800, '#30475e');
    if (series.edgeLabel) strengthenTextStyle(series.edgeLabel, 13, 700, '#334e63');
    if (series.markPoint && series.markPoint.label) strengthenTextStyle(series.markPoint.label, 13, 700);
    if (series.markLine && series.markLine.label) strengthenTextStyle(series.markLine.label, 13, 700);
    if (series.markArea && series.markArea.label) strengthenTextStyle(series.markArea.label, 13, 700);
    if (Array.isArray(series.data)) {
      series.data.forEach(function (item) {
        if (item && typeof item === 'object' && !Array.isArray(item) && item.label !== false) {
          item.label = strengthenTextStyle(item.label || {}, labelSize, denseHeatmap ? 700 : 800, '#30475e');
        }
      });
    }
    if (series.type === 'gauge' && series.detail && typeof series.detail === 'object') {
      series.detail.fontSize = Math.max(Number(series.detail.fontSize) || 0, 20);
      series.detail.fontWeight = normalizedWeight(series.detail.fontWeight, 800);
      if (series.title) strengthenTextStyle(series.title, 14, 700, '#5d7488');
    }
  }

  window.animateNumber = function (target, value, suffix, decimals, duration) {
    const el = typeof target === 'string' ? document.getElementById(target) : target;
    if (!el) return;
    const end = Number(value);
    if (!Number.isFinite(end)) { el.textContent = String(value == null ? '-' : value); return; }
    const tail = suffix || '';
    const digits = Number.isFinite(decimals) ? decimals : (String(value).includes('.') ? 1 : 0);
    if (!window.APP_MOTION) { el.textContent = end.toFixed(digits) + tail; return; }
    const started = performance.now();
    const period = duration || 850;
    function tick(now) {
      const p = Math.min(1, (now - started) / period);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = (end * eased).toFixed(digits) + tail;
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  };

  window.registerChart = function (id, option) {
    window.CHART_OPTIONS[id] = option;
    return option;
  };

  window.replayChart = function (id) {
    const c = window.CHART_REGISTRY && window.CHART_REGISTRY[id];
    const option = window.CHART_OPTIONS[id];
    if (!c || !option) return;
    c.clear();
    c.setOption(option, true);
  };

  window.startFocusLoop = function (id, seriesIndex, dataCount, interval) {
    const c = window.CHART_REGISTRY && window.CHART_REGISTRY[id];
    if (!c || !window.APP_MOTION || !dataCount) return;
    let i = 0;
    const period = interval || 1900;
    const timer = setInterval(function () {
      c.dispatchAction({ type: 'downplay', seriesIndex: seriesIndex });
      c.dispatchAction({ type: 'highlight', seriesIndex: seriesIndex, dataIndex: i });
      i = (i + 1) % dataCount;
    }, period);
    c.__motionTimer = timer;
    return timer;
  };

  window.pulseScatter = function (id, seriesIndex, interval) {
    const c = window.CHART_REGISTRY && window.CHART_REGISTRY[id];
    if (!c || !window.APP_MOTION) return;
    let up = true;
    const timer = setInterval(function () {
      c.dispatchAction({ type: 'downplay', seriesIndex: seriesIndex });
      c.dispatchAction({ type: 'highlight', seriesIndex: seriesIndex });
      up = !up;
    }, interval || 2400);
    c.__pulseTimer = timer;
  };

  window.motionDefaults = function (option) {
    if (!option) return option;
    option.animation = option.animation === false ? false : window.APP_MOTION;
    option.animationDuration = option.animationDuration || 950;
    option.animationDurationUpdate = option.animationDurationUpdate || 650;
    option.animationEasing = option.animationEasing || 'cubicOut';
    option.animationEasingUpdate = option.animationEasingUpdate || 'cubicInOut';
    option.backgroundColor = option.backgroundColor || 'transparent';
    option.color = option.color || CRC_PALETTE;
    option.textStyle = strengthenTextStyle(Object.assign({ fontFamily: CHART_FONT_FAMILY }, option.textStyle || {}), 14, 600, '#30475e');
    const tooltips = option.tooltip ? (Array.isArray(option.tooltip) ? option.tooltip : [option.tooltip]) : [];
    tooltips.forEach(function (tooltip) {
      if (!tooltip || typeof tooltip !== 'object') return;
      tooltip.textStyle = strengthenTextStyle(Object.assign({ fontFamily: CHART_FONT_FAMILY }, tooltip.textStyle || {}), 14, 600, '#f4f8fb');
      tooltip.textStyle.color = tooltip.textStyle.color || '#f4f8fb';
      tooltip.backgroundColor = tooltip.backgroundColor || 'rgba(7,29,48,.94)';
      tooltip.borderColor = tooltip.borderColor || 'rgba(80,132,235,.45)';
      tooltip.borderWidth = tooltip.borderWidth || 1;
      tooltip.padding = tooltip.padding || 10;
    });
    const legends = option.legend ? (Array.isArray(option.legend) ? option.legend : [option.legend]) : [];
    legends.forEach(function (legend) {
      if (!legend || typeof legend !== 'object') return;
      legend.textStyle = strengthenTextStyle(Object.assign({ fontFamily: CHART_FONT_FAMILY }, legend.textStyle || {}), 15, 700, '#334e63');
      legend.itemWidth = Math.max(Number(legend.itemWidth) || 0, 16);
      legend.itemHeight = Math.max(Number(legend.itemHeight) || 0, 12);
      legend.itemGap = Math.max(Number(legend.itemGap) || 0, 16);
    });
    const titles = option.title ? (Array.isArray(option.title) ? option.title : [option.title]) : [];
    titles.forEach(function (title) {
      if (!title || typeof title !== 'object') return;
      if (title.textStyle) strengthenTextStyle(title.textStyle, 16, 800, '#173b56');
      if (title.subtextStyle) strengthenTextStyle(title.subtextStyle, 14, 600, '#5d7488');
    });
    [option.xAxis, option.yAxis].forEach(function (axis) {
      if (Array.isArray(axis)) axis.forEach(strengthenAxis); else strengthenAxis(axis);
    });
    if (Array.isArray(option.series)) option.series.forEach(strengthenSeries);
    else if (option.series) strengthenSeries(option.series);
    if (option.radar && option.radar.axisName) {
      option.radar.axisName.fontSize = Math.max(Number(option.radar.axisName.fontSize) || 0, 14);
      option.radar.axisName.fontWeight = normalizedWeight(option.radar.axisName.fontWeight, 700);
      option.radar.axisName.color = option.radar.axisName.color || '#30475e';
    }
    const visualMaps = option.visualMap ? (Array.isArray(option.visualMap) ? option.visualMap : [option.visualMap]) : [];
    visualMaps.forEach(function (visualMap) {
      if (visualMap && visualMap.textStyle) strengthenTextStyle(visualMap.textStyle, 12, 700, '#40566c');
    });
    if (option.graphic) {
      const graphics = Array.isArray(option.graphic) ? option.graphic : [option.graphic];
      graphics.forEach(function (g) { if (g && g.style) strengthenTextStyle(g.style, 13, 700); });
    }
    const grids = option.grid ? (Array.isArray(option.grid) ? option.grid : [option.grid]) : [];
    grids.forEach(function (grid) { if (grid && grid.containLabel === undefined) grid.containLabel = true; });
    return option;
  };

  function initReveals() {
    const nodes = Array.prototype.slice.call(document.querySelectorAll('.reveal'));
    if (!nodes.length) return;
    if (!window.APP_MOTION || !('IntersectionObserver' in window)) {
      nodes.forEach(function (n) { n.classList.add('is-visible'); });
      return;
    }
    const observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -36px 0px' });
    nodes.forEach(function (n, i) {
      n.style.transitionDelay = Math.min(i * 55, 260) + 'ms';
      observer.observe(n);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    initReveals();
    document.documentElement.classList.add('motion-ready');
  });
})();
