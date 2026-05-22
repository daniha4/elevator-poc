/* auth.js — Netlify Edge Function
 *
 * Mode B: Login once → 90-day cookie → no more prompts
 *
 * Paths that bypass auth (PWA must work without login):
 *   /__login   — the login page itself
 *   /sw.js     — Service Worker (needed for PWA install)
 *   /manifest.json — PWA manifest (needed for PWA install)
 *
 * Everything else — including /pdfs/* — requires auth.
 *
 * To DISABLE auth (open development):
 *   Comment out the [[edge_functions]] block in netlify.toml
 *   AND rename this file to auth.js.disabled
 *   (The export const config below makes it self-activating.)
 */

const OPEN_PATHS = ["/sw.js", "/manifest.json"];
const COOKIE     = "__elev";
const MAX_AGE    = 86400 * 90; // 90 days

/* Hostnames that bypass auth entirely (dev / local) */
const DEV_HOSTS  = ["localhost", "127.0.0.1"];
function isDevHost(hostname) {
  return hostname.startsWith("dev-") || DEV_HOSTS.includes(hostname);
}

export default async function auth(request, context) {
  const url      = new URL(request.url);
  const PASSWORD = Deno.env.get("SITE_PASSWORD") || "";
  const TOKEN    = Deno.env.get("SESSION_TOKEN")  || "";

  /* ── Dev / local hosts → no auth at all ── */
  if (isDevHost(url.hostname)) return context.next();

  /* ── Paths that are always public (PWA requirements) ── */
  if (OPEN_PATHS.includes(url.pathname) || url.pathname === "/__login") {
    if (url.pathname !== "/__login") return context.next();

    /* Login GET */
    if (request.method !== "POST") {
      const next = url.searchParams.get("next") || "/";
      return html(loginHtml(next, ""));
    }

    /* Login POST */
    const form = await request.formData();
    const pw   = (form.get("password") || "").toString();
    const next = (form.get("next") || "/").toString();

    if (pw === PASSWORD && PASSWORD.length > 0) {
      const r = new Response(null, { status: 302, headers: { Location: next } });
      r.headers.set("Set-Cookie",
        `${COOKIE}=${TOKEN}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${MAX_AGE}`);
      return r;
    }
    return html(loginHtml(next, "סיסמה שגויה"), 401);
  }

  /* ── Check session cookie ── */
  if (getCookie(request, COOKIE) === TOKEN && TOKEN.length > 0) {
    return context.next();
  }

  /* ── Not authenticated → redirect to login ── */
  return new Response(null, {
    status: 302,
    headers: { Location: `/__login?next=${encodeURIComponent(url.pathname)}` },
  });
}

function getCookie(request, name) {
  const h = request.headers.get("Cookie") || "";
  for (const part of h.split(";")) {
    const eq = part.indexOf("=");
    if (eq < 0) continue;
    if (part.slice(0, eq).trim() === name) return part.slice(eq + 1).trim();
  }
  return null;
}

function html(body, status = 200) {
  return new Response(body, { status, headers: { "Content-Type": "text/html;charset=utf-8" } });
}

function loginHtml(next, error) {
  return `<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>כניסה — מערכת תקלות</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#0A0A0A;color:#F2F2F2;font-family:system-ui,sans-serif;
       display:flex;align-items:center;justify-content:center;min-height:100vh}
  .card{background:#181818;border:1px solid #252525;border-radius:14px;
        padding:2rem;width:300px}
  h2{font-size:1.1rem;margin-bottom:1.5rem;text-align:center;color:#aaa}
  .logo{text-align:center;font-size:2.5rem;margin-bottom:.75rem}
  input[type=password]{width:100%;background:#111;border:1px solid #333;
    color:#F2F2F2;padding:.8rem 1rem;border-radius:8px;font-size:1rem;
    margin-bottom:.75rem;outline:none}
  input[type=password]:focus{border-color:#1E88E5}
  button{width:100%;background:#1E88E5;color:#fff;border:none;
         padding:.8rem;border-radius:8px;font-size:1rem;cursor:pointer;font-weight:600}
  button:active{background:#1565C0}
  .err{color:#EF5350;font-size:.85rem;margin-bottom:.75rem;text-align:center}
  .hint{color:#555;font-size:.78rem;text-align:center;margin-top:1rem}
</style>
</head>
<body>
<div class="card">
  <div class="logo">🔒</div>
  <h2>מערכת קודי תקלות</h2>
  ${error ? `<div class="err">${error}</div>` : ""}
  <form method="POST" action="/__login">
    <input type="hidden" name="next" value="${next}">
    <input type="password" name="password" placeholder="סיסמה" autofocus required>
    <button type="submit">כניסה</button>
  </form>
  <div class="hint">כניסה אחת ל-90 יום</div>
</div>
</body>
</html>`;
}

/* Self-activating route — Netlify picks this up automatically.
 * To fully disable: rename file to auth.js.disabled           */
export const config = { path: "/*" };
