# מנהל הטוקנים | DN

לוח בקרה מקומי לניתוח שימוש בטוקנים של Claude Code. קורא את קובצי ה-JSONL ש-Claude Code שומר תחת `~/.claude/projects/` והופך אותם לתצוגות עלות, היסטוריית שיחות, ניתוח פרומפטים יקרים, מפת שימוש בכלים, ניתוח מטמון, השוואה בין פרויקטים, וניתוח שימוש במיומנויות.

![סקירה כללית - KPIs, עלות משוערת, כתיבה וקריאה למטמון](docs/images/dashboard-overview.png)

![סקילים - הסקילים המובילים לפי הפעלות](docs/images/dashboard-skills.png)

## פרטיות מלאה

הכלי רץ אך ורק במחשב שלך. אין טלמטריה, אין שליחת נתונים החוצה, אין שיחות לרשת חיצונית. השרת מאזין על `127.0.0.1:8080` בלבד. כל הנכסים (ECharts, Heebo, אייקונים) מסופקים מקומית מתיקיית `web/`.

לאימות עצמאי: ראו `PRIVACY_AUDIT.md` בתיקיית הפרויקט.

## דרישות מערכת

- Python 3.8 ומעלה
- Claude Code מותקן עם לפחות שיחה אחת קיימת תחת `~/.claude/projects/`
- דפדפן מודרני (Chrome, Edge, Firefox)
- ללא צורך ב-`pip install`. הכלי משתמש בספריית התקן של Python בלבד.

## הרצה

```bash
git clone https://github.com/DvirNaaman/dvir-token-manager.git
cd dvir-token-manager
python cli.py dashboard
```

הפקודה תפעיל את השרת ב-`http://127.0.0.1:8080` ותפתח אותו אוטומטית בדפדפן. השרת סורק מחדש כל 30 שניות ושולח עדכונים בזמן אמת דרך SSE, כך שלא צריך לרענן ידנית.

לעצירה: `Ctrl+C`.

## פקודות CLI נוספות

```bash
python cli.py scan      # סריקה ידנית של קובצי JSONL חדשים
python cli.py today     # סיכום של היום בטרמינל
python cli.py stats     # סיכום מאז ומתמיד בטרמינל
python cli.py tips      # הצעות לחיסכון מבוססות דפוסי שימוש
```

לכל פקודה אפשר להוסיף `--db PATH` ו-`--projects-dir PATH` לעקיפת ברירות המחדל.

## משתני סביבה

| משתנה | ברירת מחדל | תפקיד |
|---|---|---|
| `HOST` | `127.0.0.1` | כתובת ההאזנה של השרת |
| `PORT` | `8080` | פורט ההאזנה |
| `CLAUDE_PROJECTS_DIR` | `~/.claude/projects` | מקור קובצי ה-JSONL |
| `TOKEN_DASHBOARD_DB` | `~/.claude/token-dashboard.db` | מיקום מסד הנתונים SQLite המקומי |

## קיצור דרך לטשטוש פרטיות

לחיצה על `Ctrl + B` בכל מקום בלוח הבקרה מטשטשת את טקסט הפרומפטים והתכנים הרגישים, לצורך צילומי מסך. לחיצה נוספת מבטלת.

## כיצד לאמת ש-0 קריאות יוצאות

```bash
grep -rEi "https?://(?!127\.0\.0\.1|localhost)" --include="*.py" --include="*.js" --include="*.html" --include="*.css" .
```

הפלט אמור להיות ריק (פרט להערות בתוך LICENSE headers של ECharts).

## קרדיטים ורישיון

- **מנוע המקור:** [Nathan Herkelman](https://github.com/nateherkai) — פיתח את הקוד המקורי של מנתח ה-JSONL ולוח הבקרה, שוחרר תחת רישיון MIT.
- **התאמה לעברית, RTL, UI וברנדינג:** [Dvir Naaman](https://github.com/DvirNaaman) — שכתוב מלא של ממשק המשתמש, תרגום, פלטת Meridian, גופן Heebo מקומי, מערכת טיפים, ואייקונוגרפיה.

הפרויקט כולו מופץ תחת רישיון MIT (ראו קובץ `LICENSE`). אתם מוזמנים להשתמש, לשנות ולהפיץ — תוך שמירה על שתי שורות ה-copyright בקובץ הרישיון.

## תקלות נפוצות

**טקסט עברי מקודד שגוי בטרמינל ב-Windows:** הריצו פעם אחת `chcp 65001` בחלון ה-CMD לפני הפקודה, או השתמשו ב-PowerShell / Windows Terminal שתומכים ב-UTF-8 כברירת מחדל.

**הלוח ריק:** ודאו שיש לפחות שיחה אחת תחת `~/.claude/projects/<slug>/<session>.jsonl`. אם אתם בסביבה לא סטנדרטית, הצביעו ידנית עם `--projects-dir`.

**הפורט תפוס:** הפעילו עם פורט אחר: `PORT=8090 python cli.py dashboard`.
