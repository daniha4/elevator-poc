/* functions/api/analyze.js — Cloudflare Pages Function
 * POST /api/analyze
 * Body: { mfr, ctrl, code, symptom, localSnippet, availableDocs }
 * Env:  CLAUDE_API_KEY  (Cloudflare Dashboard → Pages → elevator-prod → Variables)
 */

const SYSTEM = `אתה מומחה בכיר לתחזוקת מעליות עם ניסיון של 20 שנה בשטח.
אתה מנתח תקלות עבור טכנאים בזמן אמת — בשטח, מול המעלית.
כתוב תמיד בעברית. היה ספציפי, מעשי, ממוקד.
בסס את תשובתך על הידע הטכני הרשמי של היצרן.
אם אינך בטוח — אמור זאת במפורש. אל תמציא קודים או חלקים.
הוסף רמזים מעשיים שטכנאי מנוסה יודע: מתח צפוי, נקודות בדיקה, תסמינים נלווים.`;

function buildPrompt(mfr, ctrl, code, symptom, localSnippet, availableDocs) {
  const parts = [];

  parts.push('=== פרטי התקלה ===');
  if (mfr)     parts.push(`יצרן: ${mfr}`);
  if (ctrl)    parts.push(`בקר: ${ctrl}`);
  if (code)    parts.push(`קוד תקלה: ${code}`);
  if (symptom) parts.push(`סימפטום: ${symptom}`);

  if (localSnippet) {
    parts.push('');
    parts.push('=== נתונים ממאגר הקודים המקומי ===');
    parts.push(localSnippet);
  }

  if (availableDocs) {
    parts.push('');
    parts.push('=== מסמכי יצרן זמינים לעיון ===');
    parts.push(availableDocs);
  }

  parts.push('');
  parts.push(`=== בקשה ===
ספק ניתוח מקצועי מלא בדיוק בפורמט הבא — ארבעה סעיפים, כל אחד בשורה חדשה:

**משמעות:** [הסבר מה הבקר מדווח — בשורה אחת ברורה]

**מה לבדוק:**
- [פריט ספציפי 1 — כולל מתח / נקודת מדידה אם רלוונטי]
- [פריט ספציפי 2]
- [פריט ספציפי 3]
- [פריט 4 אם נדרש]

**פעולה מומלצת:** [צעדים לפי סדר עדיפות — מה לעשות קודם]

**סיבות שכיחות:** [הגורמים הנפוצים ביותר לתקלה זו לפי ניסיון שטח]`);

  return parts.join('\n');
}

export async function onRequestPost(context) {
  const { request, env } = context;

  const apiKey = env.CLAUDE_API_KEY;
  if (!apiKey) {
    return json(
      { error: 'חסר מפתח Claude — הוסף CLAUDE_API_KEY ב-Cloudflare Dashboard → Pages → elevator-prod → Settings → Environment variables' },
      503
    );
  }

  let body;
  try { body = await request.json(); }
  catch { return json({ error: 'בקשה לא תקינה — JSON שגוי' }, 400); }

  const { mfr, ctrl, code, symptom, localSnippet, availableDocs } = body;

  if (!mfr && !code && !symptom) {
    return json({ error: 'חסר מידע — יש לספק יצרן, קוד תקלה, או סימפטום' }, 400);
  }

  const prompt = buildPrompt(mfr, ctrl, code, symptom, localSnippet, availableDocs);

  let claudeRes;
  try {
    claudeRes = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-6',
        max_tokens: 2000,
        system: SYSTEM,
        messages: [{ role: 'user', content: prompt }],
      }),
    });
  } catch (e) {
    return json({ error: 'שגיאת רשת לשרת Claude: ' + e.message }, 502);
  }

  if (!claudeRes.ok) {
    const errText = await claudeRes.text().catch(() => '');
    return json({ error: `Claude API נכשל (${claudeRes.status}) — בדוק תקפות מפתח`, detail: errText }, 502);
  }

  const data = await claudeRes.json();
  const analysis = data?.content?.[0]?.text || '';

  if (!analysis) {
    return json({ error: 'Claude החזיר תגובה ריקה' }, 502);
  }

  return json({ analysis });
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
}
