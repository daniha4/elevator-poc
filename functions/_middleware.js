/* _middleware.js — Cloudflare Pages Function
 *
 * Runs on every request (global middleware).
 * Same logic as the old Netlify auth.js — login once → 90-day cookie.
 *
 * Public paths (no auth required):
 *   /__login        login page
 *   /sw.js          Service Worker (PWA requirement)
 *   /manifest.json  PWA manifest
 *
 * Dev hosts bypass auth entirely:
 *   Hostnames starting with "dev-"  (e.g. dev-elevator.pages.dev)
 *   localhost / 127.0.0.1
 *
 * Env vars (set in Cloudflare Dashboard → Pages → Settings → Variables):
 *   SITE_PASSWORD   plain-text password
 *   SESSION_TOKEN   random secret string (token stored in cookie)
 */

const COOKIE   = '__elev';
const MAX_AGE  = 86400 * 90; // 90 days
const OPEN     = ['/sw.js', '/manifest.json'];
const DEV_IPS  = ['localhost', '127.0.0.1'];

function isDevHost(hostname) {
  return hostname.startsWith('dev-') || DEV_IPS.includes(hostname);
}

function getCookie(request, name) {
  const h = request.headers.get('Cookie') || '';
  for (const part of h.split(';')) {
    const eq = part.indexOf('=');
    if (eq < 0) continue;
    if (part.slice(0, eq).trim() === name) return part.slice(eq + 1).trim();
  }
  return null;
}

export async function onRequest(context) {
  const { request, env, next } = context;
  const url      = new URL(request.url);
  const PASSWORD = env.SITE_PASSWORD || '';
  const TOKEN    = env.SESSION_TOKEN  || '';

  /* ── Dev / local → no auth ── */
  if (isDevHost(url.hostname)) return next();

  /* ── Always-public paths ── */
  if (OPEN.includes(url.pathname)) return next();

  /* ── Login page ── */
  if (url.pathname === '/__login') {
    const nextUrl = url.searchParams.get('next') || '/';

    if (request.method !== 'POST') {
      return html(loginPage(nextUrl, ''));
    }

    const form = await request.formData();
    const pw   = (form.get('password') || '').toString();
    const dest = (form.get('next') || '/').toString();

    if (pw === PASSWORD && PASSWORD.length > 0) {
      return new Response(null, {
        status: 302,
        headers: {
          Location: dest,
          'Set-Cookie': `${COOKIE}=${TOKEN}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${MAX_AGE}`,
        },
      });
    }
    return html(loginPage(dest, 'סיסמה שגויה'), 401);
  }

  /* ── Check session cookie ── */
  if (getCookie(request, COOKIE) === TOKEN && TOKEN.length > 0) {
    return next();
  }

  /* ── Not authenticated → redirect ── */
  return new Response(null, {
    status: 302,
    headers: { Location: `/__login?next=${encodeURIComponent(url.pathname)}` },
  });
}

function html(body, status = 200) {
  return new Response(body, { status, headers: { 'Content-Type': 'text/html;charset=utf-8' } });
}

function loginPage(next, error) {
  return `<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>כניסה — מערכת תקלות</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#07090E;color:#C9D3E0;font-family:system-ui,sans-serif;
       display:flex;align-items:center;justify-content:center;min-height:100vh}
  .card{background:#111720;border:1px solid #1A2232;border-radius:14px;padding:2rem;width:300px}
  .logo{text-align:center;font-size:2.5rem;margin-bottom:.75rem}
  h2{font-size:1.05rem;margin-bottom:1.5rem;text-align:center;color:#4A5568}
  input[type=password]{width:100%;background:#07090E;border:1px solid #243040;
    color:#E8EDF3;padding:.8rem 1rem;border-radius:8px;font-size:1rem;
    margin-bottom:.75rem;outline:none}
  input[type=password]:focus{border-color:#2563EB}
  button{width:100%;background:#2563EB;color:#fff;border:none;
         padding:.8rem;border-radius:8px;font-size:1rem;cursor:pointer;font-weight:700}
  button:active{background:#1D4ED8}
  .err{color:#FC8181;font-size:.85rem;margin-bottom:.75rem;text-align:center}
  .hint{color:#2D3748;font-size:.78rem;text-align:center;margin-top:1rem}
</style>
</head>
<body>
<div class="card">
  <div class="logo">🔒</div>
  <h2>מערכת קודי תקלות</h2>
  ${error ? `<div class="err">${error}</div>` : ''}
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
