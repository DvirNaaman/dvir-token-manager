import { api, state, $ } from '/web/app.js';

export default async function (root) {
  const cur = await api('/api/plan');
  const plans = Object.entries(cur.pricing.plans);
  root.innerHTML = `
    <div class="card">
      <h2>הגדרות</h2>
      <h3 style="margin-top:16px">תוכנית</h3>
      <p class="muted" style="margin:0 0 12px">קובע כיצד מוצגת העלות. במצב API מוצגים תעריפים לפי שימוש בטוקנים. במצב מנוי מוצג הסכום החודשי הקבוע.</p>
      <div class="flex">
        <select id="plan">
          ${plans.map(([k,v]) => `<option value="${k}" ${k===cur.plan?'selected':''}>${v.label}${v.monthly?` · $${v.monthly} בחודש`:''}</option>`).join('')}
        </select>
        <button class="primary" id="save">שמור</button>
        <span id="msg" class="muted"></span>
      </div>

      <hr class="divider">

      <h3>טבלת תמחור</h3>
      <p class="muted" style="margin:0 0 12px">לעריכת תעריפים ניתן לערוך את <code>pricing.json</code> בתיקיית הפרויקט. רענון הדף לאחר העריכה.</p>
      <table>
        <thead><tr><th>מודל</th><th class="num">קלט</th><th class="num">פלט</th><th class="num">קריאת זיכרון</th><th class="num">זיכרון 5 דקות</th><th class="num">זיכרון שעה</th></tr></thead>
        <tbody>
          ${Object.entries(cur.pricing.models).map(([k,v]) => `
            <tr><td><span class="badge ${v.tier}">${k}</span></td>
              <td class="num">$${v.input.toFixed(2)}</td>
              <td class="num">$${v.output.toFixed(2)}</td>
              <td class="num">$${v.cache_read.toFixed(2)}</td>
              <td class="num">$${v.cache_create_5m.toFixed(2)}</td>
              <td class="num">$${v.cache_create_1h.toFixed(2)}</td>
            </tr>`).join('')}
        </tbody>
      </table>
      <p class="muted" style="margin-top:8px;font-size:11px">תעריפים למיליון טוקנים, בדולר אמריקאי.</p>

      <hr class="divider">

      <h3>פרטיות</h3>
      <p class="muted">לחיצה על <code>Ctrl + B</code> בכל מקום מטשטשת טקסט פרומפטים ותכנים רגישים, לצורך צילומי מסך.</p>
    </div>`;

  $('#save').addEventListener('click', async () => {
    const plan = $('#plan').value;
    await fetch('/api/plan', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ plan }) });
    state.plan = plan;
    document.getElementById('plan-pill').textContent = plan;
    $('#msg').textContent = 'נשמר.';
    $('#msg').style.color = 'var(--good)';
  });
}
