import { api, fmt } from '/web/app.js';

export default async function (root) {
  const tips = await api('/api/tips');
  root.innerHTML = `
    <div class="card">
      <h2>טיפים לחיסכון</h2>
      ${tips.length === 0
        ? '<p class="muted">אין הצעות פעילות כרגע. מנהל הטוקנים מזהה דפוסים מדי שבוע, נסו שוב לאחר פעילות נוספת.</p>'
        : `<p class="muted" style="margin:-8px 0 14px">זיהוי דפוסים מבוסס חוקים על שבעת הימים האחרונים. טיפים שנדחו חוזרים להופיע לאחר 14 יום.</p>`}
      ${tips.map(t => `
        <div class="tip">
          <div class="tip-head">
            <span class="badge">${fmt.htmlSafe(t.category)}</span>
            <strong>${fmt.htmlSafe(t.title)}</strong>
            <span class="spacer"></span>
            <button class="ghost" data-key="${fmt.htmlSafe(t.key)}">דחה</button>
          </div>
          <p class="tip-body">${fmt.htmlSafe(t.body)}</p>
        </div>`).join('')}
    </div>`;
  root.querySelectorAll('button[data-key]').forEach(b => {
    b.addEventListener('click', async () => {
      await fetch('/api/tips/dismiss', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: b.dataset.key }),
      });
      location.reload();
    });
  });
}
