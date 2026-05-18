import { api, fmt, state } from '/web/app.js';
import { barChart, donutChart, groupedBarChart, stackedBarChart } from '/web/charts.js';

const RANGES = [
  { key: '7d',  label: '7 ימים',  days: 7 },
  { key: '30d', label: '30 יום',  days: 30 },
  { key: '90d', label: '90 יום',  days: 90 },
  { key: 'all', label: 'הכול',    days: null },
];

function readRange() {
  const q = (location.hash.split('?')[1] || '');
  const m = /(?:^|&)range=([^&]+)/.exec(q);
  const k = m && decodeURIComponent(m[1]);
  return RANGES.find(r => r.key === k) || RANGES[1];
}

function writeRange(key) {
  const base = (location.hash.replace(/^#/, '').split('?')[0]) || '/overview';
  location.hash = '#' + base + '?range=' + encodeURIComponent(key);
}

function sinceIso(range) {
  if (!range.days) return null;
  return new Date(Date.now() - range.days * 86400 * 1000).toISOString();
}

function withSince(url, since) {
  if (!since) return url;
  return url + (url.includes('?') ? '&' : '?') + 'since=' + encodeURIComponent(since);
}

export default async function (root) {
  const range = readRange();
  const since = sinceIso(range);

  const [totals, projects, sessions, tools, daily, byModel] = await Promise.all([
    api(withSince('/api/overview', since)),
    api(withSince('/api/projects', since)),
    api(withSince('/api/sessions?limit=10', since)),
    api(withSince('/api/tools', since)),
    api(withSince('/api/daily', since)),
    api(withSince('/api/by-model', since)),
  ]);

  const cacheCreate =
    (totals.cache_create_5m_tokens || 0) +
    (totals.cache_create_1h_tokens || 0);

  const kpi = (label, compactVal, fullVal, cls = '') => `
    <div class="card kpi ${cls}">
      <div class="label">${label}</div>
      <div class="value" title="${fullVal}">${compactVal}</div>
    </div>`;

  const rangeTabs = `
    <div class="range-tabs" role="tablist">
      ${RANGES.map(r => `<button data-range="${r.key}" class="${r.key === range.key ? 'active' : ''}">${r.label}</button>`).join('')}
    </div>`;

  const rangeLabel = range.days ? `ב${range.days} הימים האחרונים` : 'מאז ומתמיד';

  root.innerHTML = `
    <div class="flex" style="margin-bottom:14px">
      <h2 style="margin:0;font-size:17px;letter-spacing:-0.005em">סקירה כללית</h2>
      <span class="muted" style="font-size:12px">${rangeLabel}</span>
      <div class="spacer"></div>
      ${rangeTabs}
    </div>

    <div class="row cols-7">
      ${kpi('שיחות',           fmt.int(totals.sessions),       fmt.int(totals.sessions))}
      ${kpi('סשנים',            fmt.int(totals.turns),          fmt.int(totals.turns))}
      ${kpi('קלט',              fmt.compact(totals.input_tokens),       fmt.int(totals.input_tokens) + ' טוקנים')}
      ${kpi('פלט',              fmt.compact(totals.output_tokens),      fmt.int(totals.output_tokens) + ' טוקנים')}
      ${kpi('קריאות מהזיכרון',    fmt.compact(totals.cache_read_tokens),  fmt.int(totals.cache_read_tokens) + ' טוקנים')}
      ${kpi('כתיבה לזיכרון',      fmt.compact(cacheCreate),               fmt.int(cacheCreate) + ' טוקנים')}
      <div class="card kpi cost">
        <div class="label">עלות משוערת</div>
        <div class="value" title="${fmt.usd(totals.cost_usd)}">${fmt.usd(totals.cost_usd)}</div>
        <div class="sub">${rangeLabel}</div>
        ${planSubtitle()}
      </div>
    </div>

    <details class="card glossary" style="margin-top:16px">
      <summary><h3 style="display:inline-block;margin:0">מה המספרים האלה אומרים?</h3><span class="muted" style="font-size:12px"> · לחץ להרחבה</span></summary>
      <dl>
        <dt>שיחה</dt><dd>הרצה אחת של Claude Code (מהפעלה ועד יציאה). כל שיחה היא קובץ <code>.jsonl</code> אחד.</dd>
        <dt>סשן</dt><dd>הודעה אחת שלך אל Claude. כל סשן מפעיל תגובה (לעיתים עם קריאות לכלים בדרך).</dd>
        <dt>טוקני קלט</dt><dd>הטקסט החדש שאת או תוצאות הכלים שלחתם אל Claude בסשן הזה. מחויב במחיר הקלט המלא.</dd>
        <dt>טוקני פלט</dt><dd>הטקסט ש-Claude כתב בחזרה. מחויב בתעריף הגבוה ביותר ועל פי רוב הוא הסעיף הכבד בעלות.</dd>
        <dt>קריאות מהזיכרון</dt><dd>טוקנים ש-Claude שלף מתוך זיכרון (CLAUDE.md, קבצים שכבר נקראו, השיחה עד כה). זולים פי 10 מקלט חדש. מספרים גבוהים כאן הם סימן לחיסכון טוב.</dd>
        <dt>כתיבה לזיכרון</dt><dd>שמירת תוכן בזיכרון בפעם הראשונה. עלות חד-פעמית שמשתלמת בסשן הבא.</dd>
        <dt>טוקנים מחויבים</dt><dd>קלט + פלט + כתיבה לזיכרון. קריאות מהזיכרון מחויבות בנפרד ובמחיר נמוך משמעותית.</dd>
      </dl>
    </details>

    <div class="row cols-2" style="margin-top:16px">
      <div class="card">
        <h3>פעילות יומית</h3>
        <p class="muted" style="margin:-4px 0 10px;font-size:12px">הטוקנים שבהם חויבת: מה ששלחת (<b>קלט</b>), מה ש-Claude כתב (<b>פלט</b>), ומה שנשמר בזיכרון לשימוש חוזר (<b>כתיבה לזיכרון</b>).</p>
        <div id="ch-daily-billable" style="height:380px"></div>
      </div>
      <div class="card">
        <h3>קריאות יומיות מהזיכרון</h3>
        <p class="muted" style="margin:-4px 0 10px;font-size:12px"><b>קריאות מהזיכרון</b> הן שימוש חוזר זול בתוכן ש-Claude כבר ראה (כמו CLAUDE.md). העלות שלהן נמוכה פי 10 מקלט רגיל, ולכן מספר גבוה כאן הוא סימן חיובי.</p>
        <div id="ch-daily-cache" style="height:380px"></div>
      </div>
    </div>

    <div class="row cols-2" style="margin-top:16px">
      <div class="card"><h3>טוקנים לפי פרויקט</h3><div id="ch-projects" style="height:400px"></div></div>
      <div class="card">
        <h3>שימוש בטוקנים לפי מודל</h3>
        <p class="muted" style="margin:-4px 0 4px;font-size:12px">חלוקת הטוקנים המחויבים בין מודלי Claude.</p>
        <div id="ch-model" style="height:380px"></div>
      </div>
    </div>

    <div class="row cols-2" style="margin-top:16px">
      <div class="card"><h3>הכלים הנפוצים (לפי מספר קריאות)</h3><div id="ch-tools" style="height:400px"></div></div>
      <div class="card">
        <h3 style="display:flex;align-items:center"><span>השיחות האחרונות</span><span class="spacer"></span><a href="#/sessions" style="font-weight:400;font-size:12px">לכל השיחות ←</a></h3>
        <table>
          <thead><tr><th>התחלה</th><th>פרויקט</th><th class="num">טוקנים</th></tr></thead>
          <tbody>
            ${sessions.map(s => `
              <tr>
                <td class="mono">${fmt.ts(s.started)}</td>
                <td><a href="#/sessions/${encodeURIComponent(s.session_id)}">${fmt.htmlSafe(s.project_name || s.project_slug)}</a></td>
                <td class="num">${fmt.compact(s.tokens)}</td>
              </tr>`).join('') || '<tr><td colspan="3" class="muted">אין שיחות בטווח זה</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>
  `;

  // range buttons
  root.querySelectorAll('.range-tabs button').forEach(btn => {
    btn.addEventListener('click', () => writeRange(btn.dataset.range));
  });

  // billable tokens
  stackedBarChart(document.getElementById('ch-daily-billable'), {
    categories: daily.map(d => d.day),
    series: [
      { name: 'קלט',           values: daily.map(d => d.input_tokens),        color: '#F5A623' },
      { name: 'פלט',           values: daily.map(d => d.output_tokens),       color: '#FAC864' },
      { name: 'כתיבה לזיכרון',  values: daily.map(d => d.cache_create_tokens), color: '#3FB68B' },
    ],
  });

  // daily cache reads
  stackedBarChart(document.getElementById('ch-daily-cache'), {
    categories: daily.map(d => d.day),
    series: [
      { name: 'קריאות מהזיכרון', values: daily.map(d => d.cache_read_tokens), color: '#5BCEDA' },
    ],
  });

  // by-model donut
  donutChart(document.getElementById('ch-model'),
    byModel.map(m => ({
      name: fmt.modelShort(m.model) || 'לא ידוע',
      value: (m.input_tokens || 0) + (m.output_tokens || 0)
           + (m.cache_create_5m_tokens || 0) + (m.cache_create_1h_tokens || 0),
    })).filter(d => d.value > 0),
  );

  // projects
  const topProjects = projects.slice(0, 8);
  groupedBarChart(document.getElementById('ch-projects'), {
    categories: topProjects.map(p => {
      const name = p.project_name || p.project_slug;
      return name.length > 20 ? name.slice(0, 19) + '…' : name;
    }),
    series: [
      { name: 'קלט',  values: topProjects.map(p => p.input_tokens  || 0), color: '#F5A623' },
      { name: 'פלט',  values: topProjects.map(p => p.output_tokens || 0), color: '#FAC864' },
    ],
  });

  // tools
  const topTools = tools.slice(0, 8);
  barChart(document.getElementById('ch-tools'), {
    categories: topTools.map(t => t.tool_name),
    values: topTools.map(t => t.calls),
    color: '#F5A623',
  });
}

function planSubtitle() {
  if (!state.pricing || state.plan === 'api') return '';
  const p = state.pricing.plans[state.plan];
  if (!p || !p.monthly) return '';
  return `<div class="sub">משלם $${p.monthly} בחודש בתוכנית ${fmt.htmlSafe(p.label)}</div>`;
}
