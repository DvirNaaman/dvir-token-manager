import { api, fmt } from '/web/app.js';

export default async function (root) {
  const rows = await api('/api/projects');
  root.innerHTML = `
    <div class="card">
      <h2>פרויקטים</h2>
      <p class="muted" style="margin:-8px 0 14px">ממוין לפי הוצאת טוקנים מחויבים. קריאות מהזיכרון זולות יותר, ולכן עמודה גבוהה של קריאות זיכרון מצביעה על שימוש יעיל.</p>
      <table>
        <thead><tr><th>פרויקט</th><th class="num">שיחות</th><th class="num">פניות</th><th class="num">טוקנים מחויבים</th><th class="num">קריאות זיכרון</th></tr></thead>
        <tbody>
          ${rows.map(r => `
            <tr>
              <td title="${fmt.htmlSafe(r.project_slug)}">${fmt.htmlSafe(r.project_name || r.project_slug)}</td>
              <td class="num">${fmt.int(r.sessions)}</td>
              <td class="num">${fmt.int(r.turns)}</td>
              <td class="num">${fmt.int(r.billable_tokens)}</td>
              <td class="num">${fmt.int(r.cache_read_tokens)}</td>
            </tr>`).join('') || '<tr><td colspan="5" class="muted">אין פרויקטים עדיין</td></tr>'}
        </tbody>
      </table>
    </div>`;
}
