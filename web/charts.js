// charts.js - themed ECharts wrappers (Meridian Authority light palette, RTL-aware)

const PALETTE = ['#1A2B4A', '#F5A623', '#3FB68B', '#5BCEDA', '#C4841A', '#7D8AA3', '#C73237'];

const FONT = 'Heebo, system-ui, sans-serif';
const C_TEXT      = '#1A2B4A';
const C_TEXT_SOFT = '#3C4458';
const C_MUTED     = '#6B7286';
const C_LINE      = '#E4E8EF';
const C_SURFACE   = '#FFFFFF';
const C_NAVY      = '#1A2B4A';
const C_NAVY_DEEP = '#111D31';
const C_BORDER_2  = '#CDD3DD';

const BASE = {
  textStyle: { color: C_TEXT, fontFamily: FONT },
  color: PALETTE,
  // Bigger top reserves a clean strip for the legend so it never collides with bars.
  // Bigger bottom keeps rotated date labels inside the card.
  grid: { left: 56, right: 24, top: 72, bottom: 88, containLabel: true },
};

const X_AXIS = {
  axisLine:  { lineStyle: { color: C_LINE } },
  axisLabel: { color: C_MUTED, fontFamily: FONT, fontSize: 11, hideOverlap: true },
  axisTick:  { show: false },
};

const Y_AXIS = {
  axisLine:  { show: false },
  axisTick:  { show: false },
  splitLine: { lineStyle: { color: C_LINE } },
  axisLabel: { color: C_MUTED, fontFamily: FONT, fontSize: 11 },
};

const TOOLTIP = {
  trigger: 'axis',
  backgroundColor: C_NAVY_DEEP,
  borderColor: C_NAVY_DEEP,
  borderWidth: 1,
  textStyle: { color: '#F7F8FA', fontFamily: FONT, fontSize: 12 },
  padding: [8, 12],
};

// Hebrew labels render right-to-left, so we anchor the legend at the right edge,
// then add generous itemGap + a formatter that pads the label with a space so the
// next item's color swatch never kisses the previous label's letters.
const LEGEND = {
  textStyle: { color: C_TEXT_SOFT, fontFamily: FONT, fontSize: 12 },
  top: 10, right: 16, icon: 'roundRect',
  itemWidth: 10, itemHeight: 10, padding: [4, 10],
  itemGap: 24,
  formatter: name => '  ' + name,
};

// Pick a rotation that fits the number of categories.
// Many categories => steeper rotation; few => keep horizontal so labels stay readable.
function rotationFor(n) {
  if (n > 18) return 35;
  if (n > 8)  return 20;
  return 0;
}

// Force LTR on the chart container. The page is dir="rtl" (Hebrew UI), but
// ECharts computes legend / axis / label positions in pixel space assuming LTR;
// inheriting RTL from the parent causes swatches to overlap labels and Y-axis
// numbers to clip. We keep the Hebrew text content — only the layout box is LTR.
function mount(el) {
  el.style.direction = 'ltr';
  const c = echarts.init(el, null, { renderer: 'svg' });
  window.addEventListener('resize', () => c.resize());
  return c;
}

export function lineChart(el, { x, series }) {
  const c = mount(el);
  c.setOption({
    ...BASE,
    tooltip: TOOLTIP,
    legend: LEGEND,
    xAxis: { ...X_AXIS, type: 'category', data: x, boundaryGap: false },
    yAxis: { ...Y_AXIS, type: 'value' },
    series: series.map(s => ({
      ...s, type: 'line', smooth: true, showSymbol: false,
      areaStyle: { opacity: 0.14 }, lineStyle: { width: 2 },
    })),
  });
  return c;
}

export function barChart(el, { categories, values, color }) {
  const c = mount(el);
  c.setOption({
    ...BASE,
    tooltip: { ...TOOLTIP, axisPointer: { type: 'shadow' } },
    xAxis: {
      ...X_AXIS, type: 'category', data: categories,
      axisLabel: { ...X_AXIS.axisLabel, interval: 0, rotate: rotationFor(categories.length) },
    },
    yAxis: { ...Y_AXIS, type: 'value' },
    series: [{
      type: 'bar', data: values,
      itemStyle: { color: color || PALETTE[1], borderRadius: [4, 4, 0, 0] },
      barMaxWidth: 32,
    }],
  });
  return c;
}

export function stackedBarChart(el, { categories, series, formatter }) {
  const c = mount(el);
  c.setOption({
    ...BASE,
    tooltip: {
      ...TOOLTIP,
      axisPointer: { type: 'shadow' },
      valueFormatter: formatter || (v => Number(v).toLocaleString()),
    },
    legend: LEGEND,
    xAxis: {
      ...X_AXIS, type: 'category', data: categories,
      axisLabel: { ...X_AXIS.axisLabel, interval: categories.length > 20 ? 'auto' : 0, rotate: rotationFor(categories.length) },
    },
    yAxis: { ...Y_AXIS, type: 'value' },
    series: series.map((s, i) => ({
      name: s.name,
      type: 'bar',
      stack: 'total',
      data: s.values,
      itemStyle: { color: s.color || PALETTE[i % PALETTE.length] },
      barMaxWidth: 24,
      emphasis: { focus: 'series' },
    })),
  });
  return c;
}

export function groupedBarChart(el, { categories, series, formatter }) {
  const c = mount(el);
  c.setOption({
    ...BASE,
    tooltip: {
      ...TOOLTIP,
      axisPointer: { type: 'shadow' },
      valueFormatter: formatter || (v => Number(v).toLocaleString()),
    },
    legend: LEGEND,
    xAxis: {
      ...X_AXIS, type: 'category', data: categories,
      axisLabel: { ...X_AXIS.axisLabel, interval: 0, rotate: rotationFor(categories.length) },
    },
    yAxis: { ...Y_AXIS, type: 'value' },
    series: series.map((s, i) => ({
      name: s.name,
      type: 'bar',
      data: s.values,
      itemStyle: { color: s.color || PALETTE[i % PALETTE.length], borderRadius: [4, 4, 0, 0] },
      barMaxWidth: 24,
      emphasis: { focus: 'series' },
    })),
  });
  return c;
}

export function donutChart(el, data) {
  const c = mount(el);
  c.setOption({
    color: PALETTE,
    tooltip: {
      trigger: 'item',
      backgroundColor: C_NAVY_DEEP, borderColor: C_NAVY_DEEP, borderWidth: 1,
      textStyle: { color: '#F7F8FA', fontFamily: FONT },
      formatter: p => `${p.name}<br/><b>${Number(p.value).toLocaleString()}</b> טוקנים (${p.percent.toFixed(1)}%)`,
    },
    legend: {
      textStyle: { color: C_TEXT_SOFT, fontFamily: FONT, fontSize: 11 },
      bottom: 4, icon: 'roundRect', itemWidth: 8, itemHeight: 8,
      type: 'scroll', padding: [10, 4],
    },
    series: [{
      type: 'pie',
      center: ['50%', '40%'],
      radius: ['42%', '60%'],
      avoidLabelOverlap: true,
      padAngle: 2,
      itemStyle: { borderColor: C_SURFACE, borderWidth: 2, borderRadius: 4 },
      label: {
        show: true,
        position: 'inside',
        color: '#FFFFFF',
        fontSize: 12,
        fontWeight: 700,
        fontFamily: FONT,
        formatter: ({ percent }) => percent >= 6 ? percent.toFixed(0) + '%' : '',
      },
      labelLine: { show: false },
      data,
    }],
  });
  return c;
}
