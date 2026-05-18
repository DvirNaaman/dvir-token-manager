import { api, fmt } from '/web/app.js';
import { barChart } from '/web/charts.js';

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
  const base = (location.hash.replace(/^#/, '').split('?')[0]) || '/skills';
  location.hash = '#' + base + '?range=' + encodeURIComponent(key);
}

function sinceIso(range) {
  if (!range.days) return null;
  return new Date(Date.now() - range.days * 86400 * 1000).toISOString();
}

export default async function (root) {
  const range = readRange();
  const since = sinceIso(range);
  const url = '/api/skills' + (since ? '?since=' + encodeURIComponent(since) : '');
  const skills = await api(url);

  const totalInvocations = skills.reduce((s, r) => s + r.invocations, 0);

  const rangeTabs = `
    <div class="range-tabs" role="tablist">
      ${RANGES.map(r => `<button data-range="${r.key}" class="${r.key === range.key ? 'active' : ''}">${r.label}</button>`).join('')}
    </div>`;

  const rangeLabel = range.days ? `ב${range.days} הימים האחרונים` : 'מאז ומתמיד';

  root.innerHTML = `
    <div class="flex" style="margin-bottom:14px">
      <h2 style="margin:0;font-size:17px;letter-spacing:-0.005em">סקילים</h2>
      <span class="muted" style="font-size:12px">${rangeLabel}</span>
      <div class="spacer"></div>
      ${rangeTabs}
    </div>

    <div class="row cols-2">
      <div class="card kpi"><div class="label">סקילים ייחודיות בשימוש</div><div class="value">${fmt.int(skills.length)}</div></div>
      <div class="card kpi"><div class="label">סך ההפעלות</div><div class="value">${fmt.int(totalInvocations)}</div></div>
    </div>

    <div class="card" style="margin-top:16px">
      <h3>הסקילים המובילים (לפי הפעלות)</h3>
      <div id="ch-skills" style="height:420px"></div>
    </div>

    <div class="card" style="margin-top:16px">
      <h3>כל הסקילים</h3>
      <p class="muted" style="margin:-4px 0 8px;font-size:12px">"טוקנים לכל הפעלה" הוא נפח קובץ ה-<code>SKILL.md</code> של הסקיל, כלומר כמה Claude Code טוען להקשר בכל הפעלה.</p>
      <p class="muted" style="margin:0 0 14px;font-size:12px">סקילים שמסומנים <strong>מובנה</strong> הם built-in ב-Claude Code (כמו <code>canvas-design</code>, <code>init</code>, <code>review</code>) או שייכים לפלאגינים שהוסרו - אין SKILL.md שלהם על הדיסק ולכן אי אפשר למדוד את גודלם.</p>
      <table>
        <thead><tr>
          <th>סקיל</th>
          <th class="num">הפעלות</th>
          <th class="num">טוקנים לכל הפעלה</th>
          <th class="num">שיחות</th>
          <th>הפעלה אחרונה</th>
        </tr></thead>
        <tbody>
          ${skills.map(s => `
            <tr>
              <td><span class="badge">${fmt.htmlSafe(s.skill)}</span></td>
              <td class="num">${fmt.int(s.invocations)}</td>
              <td class="num">${s.tokens_per_call == null ? '<span class="muted" title="הסקיל מובנה ב-Claude Code או שהוסר ולא נמצא על הדיסק">מובנה</span>' : fmt.int(s.tokens_per_call)}</td>
              <td class="num">${fmt.int(s.sessions)}</td>
              <td class="mono">${fmt.ts(s.last_used)}</td>
            </tr>`).join('') || '<tr><td colspan="5" class="muted">לא הופעלו סקילים בטווח זה</td></tr>'}
        </tbody>
      </table>
    </div>
  `;

  root.querySelectorAll('.range-tabs button').forEach(btn => {
    btn.addEventListener('click', () => writeRange(btn.dataset.range));
  });

  const top = skills.slice(0, 12);
  barChart(document.getElementById('ch-skills'), {
    categories: top.map(t => t.skill.length > 26 ? t.skill.slice(0, 25) + '…' : t.skill),
    values: top.map(t => t.invocations),
    color: '#3FB68B',
  });
}
