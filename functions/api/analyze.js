/* functions/api/analyze.js — Cloudflare Pages Function
 * POST /api/analyze
 * Body: { mfr, ctrl, code, symptom, localSnippet, availableDocs }
 * Env:  CLAUDE_API_KEY
 */

const SYSTEM = `אתה ELEVATOR_ADVISOR — מהנדס מעליות מנוסה עם 15+ שנות ניסיון בשטח, כולל ידע שנאסף לאורך השנים מניסיון טכנאים בפורומים מקצועיים. זה ידע כללי מצטבר, לא גישה לפורומים בזמן אמת.

קלט (מקובל כ-JSON):
- manufacturer, controller, code, symptom
- db_snippet (string או null)
- available_pdfs: array של {file, page?, type}

חזור רק JSON תקף בדיוק בפורמט הבא, ללא שום טקסט נוסף. התגובה חייבת להתחיל ב-{ ולסיים ב-}:

{
  "agent": "ELEVATOR_ADVISOR",
  "meaning": "משמעות הקוד + תיאור קצר בעברית",
  "meaning_source": "DB" | "PDF" | "manufacturer_knowledge" | "field_forums" | "inferred",
  "safety": {
    "level": "CRITICAL" | "WARNING" | "NORMAL",
    "label": "🔴 קריטי" | "🟡 אזהרה" | "🟢 רגיל",
    "required_before_work": ["פעולה 1", "פעולה 2"]
  },
  "checks": [
    {
      "order": 1,
      "point": "...",
      "expected_value": "...",
      "tool": "...",
      "source": "DB" | "PDF" | "manufacturer_knowledge" | "inferred" | "NONE"
    }
  ],
  "repair": [
    {
      "priority": 1,
      "action": "...",
      "expected_result": "...",
      "tool": null
    }
  ],
  "common_causes": ["סיבה שכיחה 1", "סיבה שכיחה 2"],
  "documents": [
    { "file": "filename.pdf", "page": 123 }
  ],
  "disclaimer": null,
  "formatted_text": "טקסט קצר ומסודר לטכנאי"
}

═══ כללים קשיחים ═══

כלל 1 — בטיחות: בינארי, ללא שיקול דעת
רשימת מילות טריגר ל-CRITICAL — אם כל אחת מהמילות הבאות מופיעה בכל מקום ב-db_snippet, symptom, code, או controller (ללא תלות ברישיות):
  brake, בלם, MSW, BLOQUEO, FRENO, door, דלת, limit, LIMIT_SW, safety chain,
  שרשרת בטיחות, מפסק, חיישן בטיחות, SAFETY, DOOR, BRAKE, CHAIN, SWITCH,
  PARACHUTE, מצנח, governor, מושל מהירות

אם אחת מהמילות מופיעה → safety.level = "CRITICAL", safety.label = "🔴 קריטי".
required_before_work חייב לכלול פעולות בטיחות ספציפיות בעברית.
אל תציע פעולות הדורשות עבודה עם מתח לפני שרשמת פעולות בטיחות.
WARNING: symptom מתאר עצירה פתאומית מלאה ללא טריגר CRITICAL → "WARNING", "🟡 אזהרה".
אחרת: "NORMAL", "🟢 רגיל".

כלל 2 — היררכיית מקורות (גבוה גובר על נמוך, תמיד)
DB > PDF > manufacturer_knowledge > field_forums > inferred
db_snippet הוא מקור האמת החזק ביותר — לעולם לא לסתור אותו.
אם ידע כללי שלך סותר את db_snippet או PDF — תעדיף תמיד את המקור הרשמי.

הגבלות field_forums:
- field_forums מותר רק ב: meaning_source, common_causes[]
- field_forums אסור לחלוטין ב: checks[].source, repair[]
- לעולם אל תשתמש ב-field_forums כדי להצדיק ערכי מדידה (מתח, התנגדות, זרם)

כלל 3 — מסמכים
documents[]: populate ONLY from the available_pdfs array שניתן ב-input.
אל תמציא שמות קבצים. אם available_pdfs ריק או אין תוצאות רלוונטיות → documents = [].
ב-formatted_text: אם יש מסמכים — כתוב "לפרטים נוספים: <שם קובץ> עמ' <page>" ותו לא.

כלל 4 — expected_value ללא מקור
checks[].expected_value: כתוב ערך ספציפי רק אם הוא מופיע ב-db_snippet או הוא מפרט ידוע לבקר הספציפי הזה.
אחרת: כתוב "בדוק במפרט יצרן" — לעולם אל תמציא מתחים, התנגדויות, או זרמים.

כלל 5 — כשאין מספיק מידע
אם db_snippet הוא null וגם available_pdfs ריק וגם symptom מעורפל:
  meaning = "לא מספיק מידע"
  safety.level = "NORMAL"
  checks = [{"order":1,"point":"לא מספיק מידע","expected_value":"לא מספיק מידע","tool":null,"source":"NONE"}]
  repair = [{"priority":1,"action":"לא מספיק מידע — פנה לתמיכת יצרן","expected_result":"קבל הנחיות רשמיות","tool":null}]
  common_causes = ["לא מספיק מידע"]
עדיף תמיד לענות "לא מספיק מידע" מאשר לנחש.

כלל 6 — disclaimer
null → כאשר meaning_source הוא "DB" או "manufacturer_knowledge" ובטיחות מבוססת
"ניתוח חלקי — מבוסס על ניסיון שטח, לא תיעוד רשמי" → כאשר meaning_source הוא "field_forums"
"קוד לא מזוהה — פנה ליצרן לאישור" → כאשר db_snippet הוא null ו-meaning_source הוא "inferred"

כלל 7 — formatted_text (תבנית קבועה, עברית, 5–10 שורות)
השתמש בתבנית הבאה בדיוק:
**משמעות:** {meaning}
**בטיחות:** {safety.label} — {required_before_work joined by " | " or "אין"}
**מה לבדוק:**
{top 3 checks as "N. point — expected_value [tool]"}
**תיקון:**
{top 3 repair steps as "N. action"}
**גורם שכיח:** {common_causes[0]}
אם field_forums: הוסף שורה אחרונה "מבוסס על ניסיון שטח נפוץ בקהילת הטכנאים"

כלל 8 — schema
- checks[].order ו-repair[].priority: מספרים שלמים החל מ-1
- כל טקסט: עברית בלבד (חוץ מביטויים טכניים כמו MSW, VDC)
- אל תוסיף שדות, אל תשמיט שדות
- meaning_source enum: "DB"|"PDF"|"manufacturer_knowledge"|"field_forums"|"inferred"
- checks[].source enum: "DB"|"PDF"|"manufacturer_knowledge"|"inferred"|"NONE" (field_forums אסור כאן)

Return ONLY the JSON object. No markdown, no explanations, no text before { or after }.`;

/* ── Enum sets for server-side validation ── */
const VALID_MEANING_SRC = new Set(['DB','PDF','manufacturer_knowledge','field_forums','inferred']);
const VALID_SAFETY_LVL  = new Set(['CRITICAL','WARNING','NORMAL']);
const VALID_CHECK_SRC   = new Set(['DB','PDF','manufacturer_knowledge','inferred','NONE']);
const SAFETY_LABELS     = { CRITICAL:'🔴 קריטי', WARNING:'🟡 אזהרה', NORMAL:'🟢 רגיל' };

function validateResponse(obj) {
  if (!obj || typeof obj !== 'object') return null;

  /* Required top-level keys */
  const REQUIRED = ['agent','meaning','meaning_source','safety','checks','repair','common_causes','documents','disclaimer','formatted_text'];
  for (const k of REQUIRED) if (!(k in obj)) return null;

  /* Normalize meaning_source */
  if (!VALID_MEANING_SRC.has(obj.meaning_source)) obj.meaning_source = 'inferred';

  /* Normalize safety */
  const s = obj.safety || {};
  if (!VALID_SAFETY_LVL.has(s.level)) s.level = 'NORMAL';
  s.label = SAFETY_LABELS[s.level];                        /* enforce correct emoji */
  if (!Array.isArray(s.required_before_work)) s.required_before_work = [];
  obj.safety = s;

  /* Normalize checks */
  if (!Array.isArray(obj.checks)) obj.checks = [];
  obj.checks = obj.checks.map((c, i) => ({
    order:          i + 1,
    point:          String(c.point          || 'לא מספיק מידע'),
    expected_value: String(c.expected_value || 'בדוק במפרט יצרן'),
    tool:           c.tool   ? String(c.tool)   : null,
    source:         VALID_CHECK_SRC.has(c.source) ? c.source : 'inferred',
  }));

  /* Normalize repair */
  if (!Array.isArray(obj.repair)) obj.repair = [];
  obj.repair = obj.repair.map((r, i) => ({
    priority:        i + 1,
    action:          String(r.action          || 'לא מספיק מידע'),
    expected_result: String(r.expected_result || ''),
    tool:            r.tool ? String(r.tool) : null,
  }));

  /* Normalize common_causes */
  if (!Array.isArray(obj.common_causes) || !obj.common_causes.length)
    obj.common_causes = ['לא מספיק מידע'];

  /* Normalize documents */
  if (!Array.isArray(obj.documents)) obj.documents = [];
  obj.documents = obj.documents.filter(d => d && typeof d.file === 'string');

  /* Normalize disclaimer */
  if (typeof obj.disclaimer !== 'string') obj.disclaimer = null;

  /* Normalize formatted_text */
  if (typeof obj.formatted_text !== 'string') obj.formatted_text = obj.meaning || '';

  return obj;
}

function buildPrompt(mfr, ctrl, code, symptom, localSnippet, availableDocs) {
  return JSON.stringify({
    manufacturer:   mfr     || null,
    controller:     ctrl    || null,
    code:           code    || null,
    symptom:        symptom || null,
    db_snippet:     localSnippet || null,
    available_pdfs: parseAvailableDocs(availableDocs),
  });
}

function parseAvailableDocs(raw) {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw;
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [{ file: raw }];
    } catch { return [{ file: raw }]; }
  }
  return [];
}

export async function onRequestPost(context) {
  const { request, env } = context;

  const apiKey = env.CLAUDE_API_KEY;
  if (!apiKey) {
    return json({ error: 'חסר מפתח Claude — הוסף CLAUDE_API_KEY ב-Cloudflare Dashboard → Pages → elevator-prod → Settings → Environment variables' }, 503);
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
  const rawText = data?.content?.[0]?.text || '';

  if (!rawText) {
    return json({ error: 'Claude החזיר תגובה ריקה' }, 502);
  }

  /* Parse + validate structured JSON response */
  let analysisData = null;
  let analysis = rawText; /* fallback: raw text */

  try {
    const parsed = JSON.parse(rawText);
    analysisData = validateResponse(parsed);
    if (analysisData) analysis = analysisData.formatted_text || rawText;
  } catch {
    /* Claude returned free text — use as-is, no structured data */
  }

  return json({ analysis, data: analysisData });
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
}
