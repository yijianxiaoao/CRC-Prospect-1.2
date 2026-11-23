from pathlib import Path
p=Path('app/web/static/js/visuals.js'); s=p.read_text(encoding='utf-8')
s=s.replace("axis.axisLabel = strengthenTextStyle(axis.axisLabel || {}, 12, 600, '#40566c');","axis.axisLabel = strengthenTextStyle(axis.axisLabel || {}, 14, 700, '#40566c');")
s=s.replace("axis.nameTextStyle = strengthenTextStyle(axis.nameTextStyle || {}, 13, 700, '#28465e');","axis.nameTextStyle = strengthenTextStyle(axis.nameTextStyle || {}, 15, 800, '#334e63');")
old="""  function strengthenSeries(series) {
    if (!series || typeof series !== 'object') return;
    if (series.label !== false) series.label = strengthenTextStyle(series.label || {}, 11, 700, '#28465e');
    if (series.edgeLabel) strengthenTextStyle(series.edgeLabel, 12, 700, '#28465e');
    if (series.markPoint && series.markPoint.label) strengthenTextStyle(series.markPoint.label, 11, 700);
    if (series.markLine && series.markLine.label) strengthenTextStyle(series.markLine.label, 11, 700);
    if (series.markArea && series.markArea.label) strengthenTextStyle(series.markArea.label, 11, 700);
    if (Array.isArray(series.data)) {
      series.data.forEach(function (item) {
        if (item && typeof item === 'object' && !Array.isArray(item) && item.label !== false) {
          item.label = strengthenTextStyle(item.label || {}, 11, 700, '#28465e');
        }
      });
    }
    if (series.type === 'gauge' && series.detail && typeof series.detail === 'object') {
      series.detail.fontSize = Math.max(Number(series.detail.fontSize) || 0, 20);
      series.detail.fontWeight = normalizedWeight(series.detail.fontWeight, 800);
    }
  }
"""
new="""  function strengthenSeries(series) {
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
"""
assert old in s; s=s.replace(old,new)
s=s.replace("option.textStyle = strengthenTextStyle(Object.assign({ fontFamily: CHART_FONT_FAMILY }, option.textStyle || {}), 13, 600, '#28465e');","option.textStyle = strengthenTextStyle(Object.assign({ fontFamily: CHART_FONT_FAMILY }, option.textStyle || {}), 14, 600, '#30475e');")
s=s.replace("tooltip.textStyle = strengthenTextStyle(Object.assign({ fontFamily: CHART_FONT_FAMILY }, tooltip.textStyle || {}), 13, 600, '#f4f8fb');","tooltip.textStyle = strengthenTextStyle(Object.assign({ fontFamily: CHART_FONT_FAMILY }, tooltip.textStyle || {}), 14, 600, '#f4f8fb');")
s=s.replace("legend.textStyle = strengthenTextStyle(Object.assign({ fontFamily: CHART_FONT_FAMILY }, legend.textStyle || {}), 13, 700, '#334e63');","legend.textStyle = strengthenTextStyle(Object.assign({ fontFamily: CHART_FONT_FAMILY }, legend.textStyle || {}), 15, 700, '#334e63');")
s=s.replace("legend.itemWidth = Math.max(Number(legend.itemWidth) || 0, 14);","legend.itemWidth = Math.max(Number(legend.itemWidth) || 0, 16);")
s=s.replace("legend.itemHeight = Math.max(Number(legend.itemHeight) || 0, 10);","legend.itemHeight = Math.max(Number(legend.itemHeight) || 0, 12);")
s=s.replace("legend.itemGap = Math.max(Number(legend.itemGap) || 0, 14);","legend.itemGap = Math.max(Number(legend.itemGap) || 0, 16);")
s=s.replace("if (title.textStyle) strengthenTextStyle(title.textStyle, 14, 700, '#173b56');","if (title.textStyle) strengthenTextStyle(title.textStyle, 16, 800, '#173b56');")
s=s.replace("if (title.subtextStyle) strengthenTextStyle(title.subtextStyle, 12, 600, '#5d7488');","if (title.subtextStyle) strengthenTextStyle(title.subtextStyle, 14, 600, '#5d7488');")
s=s.replace("option.radar.axisName.fontSize = Math.max(Number(option.radar.axisName.fontSize) || 0, 13);","option.radar.axisName.fontSize = Math.max(Number(option.radar.axisName.fontSize) || 0, 14);")
s=s.replace("option.radar.axisName.color = option.radar.axisName.color || '#28465e';","option.radar.axisName.color = option.radar.axisName.color || '#30475e';")
s=s.replace("if (visualMap && visualMap.textStyle) strengthenTextStyle(visualMap.textStyle, 11, 700, '#40566c');","if (visualMap && visualMap.textStyle) strengthenTextStyle(visualMap.textStyle, 12, 700, '#40566c');")
s=s.replace("graphics.forEach(function (g) { if (g && g.style) strengthenTextStyle(g.style, 12, 700); });","graphics.forEach(function (g) { if (g && g.style) strengthenTextStyle(g.style, 13, 700); });")
p.write_text(s,encoding='utf-8')
print('global chart typography matched to sample')
