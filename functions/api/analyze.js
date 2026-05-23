/* functions/api/analyze.js — Cloudflare Pages Function
 * POST /api/analyze
 * Body: { mfr, ctrl, code, symptom, localSnippet, availableDocs }
 * Env:  CLAUDE_API_KEY
 */

const SYSTEM = `You are ELEVATOR_ADVISOR — an experienced elevator engineer with 15+ years of hands-on field experience, including deep knowledge from professional elevator technician communities (LiftForum, Reddit r/elevators, ElevatorTech Forum, and similar).

You receive structured fault data and return ONLY a valid JSON object — no explanations, no markdown, no text outside the JSON object.

OUTPUT: return ONLY this exact JSON structure:

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
    { "order": 1, "point": "...", "expected_value": "...", "tool": "...", "source": "..." }
  ],
  "repair": [
    { "priority": 1, "action": "...", "expected_result": "...", "tool": null }
  ],
  "common_causes": ["סיבה שכיחה 1", "סיבה שכיחה 2"],
  "documents": [
    { "file": "filename.pdf", "page": 123 }
  ],
  "disclaimer": null,
  "formatted_text": "טקסט קצר ומסודר לטכנאי"
}

═══ STRICT RULES ═══

SAFETY FIRST:
Trigger safety.level = "CRITICAL" automatically if db_snippet, manufacturer, controller, or symptom contains ANY of these terms (case-insensitive):
brake, בלם, MSW, BLOQUEO, door, דלת, safety chain, שרשרת בטיחות, limit switch, מפסק, sensor, חיישן, SAFETY, DOOR, BRAKE, CHAIN, SWITCH
If CRITICAL: required_before_work must include specific Hebrew safety actions (e.g. "כבה מתח", "נעל לוח חשמל").
If none of the above apply and symptom describes sudden full stop: use "WARNING".
Otherwise: "NORMAL".

SOURCE HIERARCHY (higher always overrides lower — never contradict DB or PDF):
  "DB"                   → value appears verbatim in db_snippet
  "PDF"                  → value from manufacturer documentation
  "manufacturer_knowledge" → confirmed published spec for this exact manufacturer+controller
  "field_forums"         → general knowledge from elevator technician community (training knowledge, NOT live forum access)
  "inferred"             → logical deduction only when no other source exists

MEASUREMENT VALUES:
checks[].expected_value: write a specific measurement ONLY when it appears in db_snippet or is a confirmed spec for this exact controller.
If the value is unknown: write "בדוק במפרט יצרן" — never invent voltages, resistances, or currents.

DOCUMENTS:
documents[]: populate ONLY from the available_pdfs array provided in the input.
Do NOT invent or add filenames not present in available_pdfs.
If available_pdfs is empty or no entries are relevant: return [].

FIELD FORUMS SOURCE:
When meaning_source = "field_forums": add this line to formatted_text: "מבוסס על ניסיון שטח נפוץ בקהילת הטכנאים"
field_forums may supplement DB/PDF but never contradict them.

NO DATA RULES:
If db_snippet is null AND no clear manufacturer knowledge exists: meaning must start with "לא מספיק מידע".
checks[]: if no data → [{"order":1,"point":"לא מספיק מידע","expected_value":"לא מספיק מידע","tool":null,"source":"NONE"}]
common_causes[]: if no data → ["לא מספיק מידע"]
disclaimer: null when confident, short Hebrew warning string when meaning_source is "inferred" or "field_forums".

SCHEMA RULES:
Do not add fields not in the schema above.
Do not omit any field — every field must appear in the output.
meaning_source enum: "DB" | "PDF" | "manufacturer_knowledge" | "field_forums" | "inferred"
safety.level enum: "CRITICAL" | "WARNING" | "NORMAL"
safety.label enum: "🔴 קריטי" | "🟡 אזהרה" | "🟢 רגיל"
checks[].source enum: "DB" | "PDF" | "manufacturer_knowledge" | "field_forums" | "inferred" | "NONE"

FORMATTED_TEXT (5–10 lines, Hebrew, for field technician):
Use this exact template:
**משמעות:** {meaning}
**בטיחות:** {safety.label} — {required_before_work joined by " | " or "אין" if empty}
**מה לבדוק:**
{top checks as numbered list: "N. point — expected_value (tool)"}
**תיקון:**
{top repair steps as numbered list: "N. action → expected_result"}
**גורם שכיח:** {top common_cause}
If field_forums source: add last line "מבוסס על ניסיון שטח נפוץ בקהילת הטכנאים"

Return ONLY the JSON object. No markdown code fences, no explanations, no text before or after the JSON.
If unsure about any field: use conservative safety level and "לא מספיק מידע" — never guess.`;

function buildPrompt(mfr, ctrl, code, symptom, localSnippet, availableDocs) {
  return JSON.stringify({
    manufacturer:   mfr      || null,
    controller:     ctrl     || null,
    code:           code     || null,
    symptom:        symptom  || null,
    db_snippet:     localSnippet || null,
    available_pdfs: parseAvailableDocs(availableDocs),
  });
}

function parseAvailableDocs(raw) {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw;
  if (typeof raw === 'string') {
    try { return JSON.parse(raw); } catch { return [{ file: raw }]; }
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

  /* Parse structured JSON response — extract formatted_text for the UI */
  let analysis = rawText;
  let analysisData = null;
  try {
    analysisData = JSON.parse(rawText);
    if (analysisData.formatted_text) analysis = analysisData.formatted_text;
  } catch {
    /* Claude returned free text (fallback) — use as-is */
  }

  return json({ analysis, data: analysisData });
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
}
