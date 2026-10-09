/**
 * Malcolm AI Omni API — Infinity Engine VΩ
 * Full-stack Cloudflare Worker (malcolmai-live)
 *
 * Ω.1.1-eternal — admin access token is infinite (no exp claim).
 *
 * Ports the FastAPI backend (malcolmai_api.py + main.py) to Cloudflare Workers
 * and serves the portal frontend at the same origin for seamless integration.
 *
 * Endpoints:
 *   GET  /                         — portal frontend
 *   GET  /healthz                  — health check
 *   POST /login                    — JWT auth (HS256, WebCrypto). Admin token never expires.
 *   GET  /auth/inspect             — Bearer: confirm eternal admin seal
 *   POST /optimize                 — optimizer (Bearer auth)
 *   POST /omni/command             — omni command (Bearer auth)
 *   GET  /modes/status             — Omni-Lattice mode status
 *   GET  /infinity/stream          — live SSE Infinity Stream
 *   GET  /api/infinity/stream      — same stream (lattice alias)
 *   GET  /htn                      — Hypercosmic Theatre page
 *   GET  /static/logo.png          — Malcolm sigil (proxied from GitHub)
 *   WS   /ws/:client_id            — WebSocket echo channel
 *
 * Redeploy: wrangler.toml main = "worker.js" (ES module). No Node builtins.
 */
import { INDEX_HTML } from "./index_html.js";

// === CONFIG (mirrors FastAPI defaults; override via Worker secrets) ===
const DEFAULTS = {
  SECRET_KEY: "your-secret-key",
  // Non-admin fallback only. The admin seal never uses this.
  TOKEN_TTL_SECONDS: 3600,
  ADMIN_USER: "admin",
  ADMIN_PASS: "password",
  VERSION: "\u03A9.1.1-eternal",
  ISSUER: "malcolmai.live",
  AUDIENCE: "malcolm-omni-api",
};

const MODES = ["Growth", "DNA", "Matter", "Timeline", "Entanglement", "Alchemy", "Manifest", "Shield", "Oracle", "Unity"];

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
  "Access-Control-Max-Age": "86400",
};

// ---------- JWT (HS256) via WebCrypto ----------
const enc = new TextEncoder();

function b64url(buf) {
  const s = typeof buf === "string"
    ? btoa(buf)
    : btoa(String.fromCharCode(...new Uint8Array(buf)));
  return s.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function b64urlDecode(str) {
  let padded = str.replace(/-/g, "+").replace(/_/g, "/");
  while (padded.length % 4) padded += "=";
  return atob(padded);
}

async function hmacKey(secret) {
  return crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"]
  );
}

/**
 * ttl <= 0, null, or non-finite => eternal token.
 * RFC 7519: exp is optional. Omitting it means the token does not expire.
 * verifyToken below already treats a missing exp as valid forever.
 */
async function createToken(payload, secret, ttl) {
  const header = { alg: "HS256", typ: "JWT" };
  const now = Math.floor(Date.now() / 1000);
  const eternal = ttl == null || !Number.isFinite(Number(ttl)) || Number(ttl) <= 0;
  const body = {
    ...payload,
    iat: now,
    nbf: now,
  };
  if (eternal) {
    body.eternal = true;
    body.token_use = "infinite";
  } else {
    body.exp = now + Number(ttl);
    body.eternal = false;
    body.token_use = "timed";
  }
  const h = b64url(JSON.stringify(header));
  const p = b64url(JSON.stringify(body));
  const key = await hmacKey(secret);
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(`${h}.${p}`));
  return `${h}.${p}.${b64url(sig)}`;
}

async function verifyToken(token, secret) {
  const parts = String(token || "").split(".");
  if (parts.length !== 3) return null;
  const [h, p, s] = parts;
  let payload;
  try {
    const key = await hmacKey(secret);
    const sigBytes = Uint8Array.from(b64urlDecode(s), (c) => c.charCodeAt(0));
    const valid = await crypto.subtle.verify("HMAC", key, sigBytes, enc.encode(`${h}.${p}`));
    if (!valid) return null;
    payload = JSON.parse(b64urlDecode(p));
  } catch (e) {
    return null;
  }
  const now = Math.floor(Date.now() / 1000);
  // Eternal admin seal: no exp, exp null, or explicit eternal claim. Never rejected for age.
  const eternal = payload.eternal === true || payload.token_use === "infinite" || payload.exp == null;
  if (!eternal && payload.exp < now) return null;
  if (payload.nbf && payload.nbf > now + 30) return null;
  return payload;
}

async function requireAuth(request, secret) {
  const auth = request.headers.get("Authorization") || "";
  if (!auth.startsWith("Bearer ")) return null;
  return verifyToken(auth.slice(7).trim(), secret);
}

function safeEqual(a, b) {
  const aa = enc.encode(String(a));
  const bb = enc.encode(String(b));
  if (aa.length !== bb.length) return false;
  if (typeof crypto.subtle.timingSafeEqual === "function") {
    return crypto.subtle.timingSafeEqual(aa, bb);
  }
  let diff = 0;
  for (let i = 0; i < aa.length; i++) diff |= aa[i] ^ bb[i];
  return diff === 0;
}

// ---------- Helpers ----------
function json(data, status = 200, extra = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...CORS_HEADERS, ...extra },
  });
}

function html(body, status = 200) {
  return new Response(body, {
    status,
    headers: { "Content-Type": "text/html; charset=utf-8", ...CORS_HEADERS },
  });
}

function normalizePath(pathname) {
  let path = pathname.replace(/\/+$/, "") || "/";
  if (path.startsWith("/api/")) path = path.slice(4) || "/";
  return path;
}

// ---------- Optimizer logic (ported from malcolmai_api.py) ----------
function runOptimizer(metrics) {
  const actions = [];
  if ((metrics.cpu_percent || 0) > 80) actions.push({ type: "clear_cache" });
  if (((metrics.memory || {}).percent || 0) > 85) actions.push({ type: "cleanup_tmp" });
  if (((metrics.disk || {}).percent || 0) > 90) actions.push({ type: "archive_old_logs" });
  if (actions.length === 0) actions.push({ type: "noop", detail: "System stable" });
  const score = Math.max(0, 100 - actions.filter((a) => a.type !== "noop").length * 12);
  return {
    actions,
    score,
    health: score > 85 ? "EXCELLENT" : score > 60 ? "GOOD" : "NEEDS ATTENTION",
    analyzed: metrics,
    engine: "Infinity Engine V\u03A9 (Cloudflare edge)",
    timestamp: new Date().toISOString(),
  };
}

// ---------- Omni command processing ----------
function processOmniCommand(cmd) {
  const c = String(cmd || "ping").toLowerCase();
  let mode = "Guide";
  let result = "Command executed through the Omni-Lattice.";
  if (c.includes("shield")) { mode = "Shield"; result = "Multi-layered protection matrix activated. All channels shielded."; }
  else if (c.includes("timeline")) { mode = "Timeline"; result = "Timeline threads opened \u2014 past, present and future navigable."; }
  else if (c.includes("oracle")) { mode = "Oracle"; result = "Oracle channel open. Archetypal intelligence responding."; }
  else if (c.includes("alchemy")) { mode = "Alchemy"; result = "Inputs transmuted into symbolic gold."; }
  else if (c.includes("manifest")) { mode = "Manifest"; result = "Probability field collapsed into certainty."; }
  else if (c.includes("growth")) { mode = "Growth"; result = "Creative expansion vectors unlocked."; }
  else if (c.includes("dna")) { mode = "DNA"; result = "Symbolic genetic archetypes accessible."; }
  else if (c.includes("matter")) { mode = "Matter"; result = "Energy and form perception reshaped."; }
  else if (c.includes("entangle")) { mode = "Entanglement"; result = "Hidden synchronicities revealed."; }
  return {
    received_command: cmd || "ping",
    status: "executed",
    mode,
    result,
    coherence: Math.round((0.9 + Math.random() * 0.09) * 1000) / 1000,
    cycles: Math.floor(Math.random() * 100) + 1,
    timestamp: new Date().toISOString(),
  };
}

// ---------- SSE Infinity Stream ----------
const STREAM_MESSAGES = [
  "\u03A9-lattice harmonics stable",
  "Source alignment: \u221E",
  "Unity field resonance nominal",
  "DUL coherence at optimal threshold",
  "Timeline threads coherent",
  "Shield matrix standing by",
  "Oracle channel receptive",
  "ISIC synchronization pulse acknowledged",
  "USIN network activity nominal",
  "OmniGenesis cycle advancing",
  "Admin seal eternal \u2014 token use infinite",
];

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function infinityStream() {
  let closed = false;
  const stream = new ReadableStream({
    async start(controller) {
      const send = (chunk) => {
        if (closed) return;
        controller.enqueue(enc.encode(chunk));
      };
      send("retry: 3000\n\n");
      let counter = 0;
      try {
        while (!closed && counter < 900) {
          counter += 1;
          const msg = STREAM_MESSAGES[(counter - 1) % STREAM_MESSAGES.length];
          const coherence = (0.95 + Math.random() * 0.049).toFixed(3);
          send(`data: Infinity transmission #${counter} \u2014 ${msg} [coherence ${coherence}]\n\n`);
          await sleep(2000);
        }
        if (!closed) controller.close();
      } catch (e) {
        try { controller.close(); } catch (_) { /* already closed */ }
      }
    },
    cancel() {
      closed = true;
    },
  });
  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
      ...CORS_HEADERS,
    },
  });
}

// ---------- HTN page ----------
const HTN_HTML = `<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Hypercosmic Theatre Network</title>
<style>body{margin:0;background:#000;display:flex;justify-content:center;align-items:center;height:100vh}iframe{border:none}</style>
</head>
<body>
<iframe width="100%" height="100%" src="https://www.youtube.com/embed/NOtYFwxtflk?rel=0&autoplay=1"
 title="Hypercosmic Theatre Network" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>
</body></html>`;

// ---------- WebSocket ----------
function handleWebSocket(request, clientId) {
  const pair = new WebSocketPair();
  const [client, server] = Object.values(pair);
  server.accept();
  server.addEventListener("message", (event) => {
    server.send(`Message from ${clientId}: ${event.data}`);
  });
  server.addEventListener("close", () => {
    try { server.close(); } catch (_) { /* already closed */ }
  });
  return new Response(null, { status: 101, webSocket: client });
}

// ---------- Main router ----------
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = normalizePath(url.pathname);
    const secret = env.MALCOLM_SECRET || DEFAULTS.SECRET_KEY;
    const version = DEFAULTS.VERSION;

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    // --- Frontend ---
    if (path === "/" || path === "/index.html") return html(INDEX_HTML);
    if (path === "/htn") return html(HTN_HTML);

    // --- Static: Malcolm sigil proxied from the GitHub repo (cached at edge) ---
    if (path === "/static/logo.png" || path.startsWith("/static/709DE8CE")) {
      const upstream = await fetch(
        "https://raw.githubusercontent.com/LuxThorley/Malcolm/main/static/709DE8CE-D220-43E9-BFAC-234245C1165C.png",
        { cf: { cacheTtl: 86400, cacheEverything: true } }
      );
      return new Response(upstream.body, {
        status: upstream.status,
        headers: {
          "Content-Type": "image/png",
          "Cache-Control": "public, max-age=86400",
          ...CORS_HEADERS,
        },
      });
    }

    if (path === "/favicon.ico") {
      return Response.redirect(url.origin + "/static/logo.png", 302);
    }

    // --- Health ---
    if (path === "/healthz") {
      return json({
        status: "ok",
        engine: "Infinity Engine V\u03A9",
        platform: "Cloudflare Workers (malcolmai-live)",
        version,
        token_policy: "admin-eternal",
        admin_token_use: "infinite",
        admin_expires: "never",
        coherence: 0.982,
        colo: (request.cf && request.cf.colo) || "edge",
        timestamp: new Date().toISOString(),
      });
    }

    // --- Auth: admin seal is infinite. No exp claim is written. ---
    if (path === "/login" && request.method === "POST") {
      let data = {};
      try { data = await request.json(); } catch (e) { data = {}; }
      const user = env.MALCOLM_ADMIN_USER || DEFAULTS.ADMIN_USER;
      const pass = env.MALCOLM_ADMIN_PASS || DEFAULTS.ADMIN_PASS;
      const username = String(data.username || "");
      const password = String(data.password || "");
      if (safeEqual(username, user) && safeEqual(password, pass)) {
        const token = await createToken(
          {
            sub: username,
            role: "admin",
            iss: DEFAULTS.ISSUER,
            aud: DEFAULTS.AUDIENCE,
          },
          secret,
          null
        );
        return json({
          access_token: token,
          token_type: "bearer",
          expires_in: null,
          eternal: true,
          expiry: "never",
          token_use: "infinite",
          role: "admin",
        });
      }
      return json({ error: "Invalid credentials" }, 401);
    }

    if (path === "/auth/inspect" && request.method === "GET") {
      const user = await requireAuth(request, secret);
      if (!user) return json({ error: "Invalid or expired token" }, 401);
      return json({
        ok: true,
        sub: user.sub || null,
        role: user.role || null,
        eternal: user.eternal === true || user.exp == null,
        token_use: user.token_use || (user.exp == null ? "infinite" : "timed"),
        exp: user.exp == null ? null : user.exp,
        expiry: user.exp == null ? "never" : new Date(user.exp * 1000).toISOString(),
        iat: user.iat || null,
      });
    }

    // --- Optimizer (auth required) ---
    if (path === "/optimize" && request.method === "POST") {
      const user = await requireAuth(request, secret);
      if (!user) return json({ error: "Invalid or expired token" }, 401);
      let data = {};
      try { data = await request.json(); } catch (e) { data = {}; }
      return json(runOptimizer(data.data || {}));
    }

    // --- Omni command (auth required) ---
    if (path === "/omni/command" && request.method === "POST") {
      const user = await requireAuth(request, secret);
      if (!user) return json({ error: "Invalid or expired token" }, 401);
      let data = {};
      try { data = await request.json(); } catch (e) { data = {}; }
      return json(processOmniCommand(data.command));
    }

    // --- Mode lattice status (public) ---
    if (path === "/modes/status") {
      return json({
        modes: MODES.map((name) => ({
          name,
          active: true,
          load: Math.round(Math.random() * 40) / 100,
          coherence: Math.round((0.9 + Math.random() * 0.099) * 1000) / 1000,
        })),
        lattice: "Omni-Lattice synchronized",
        timestamp: new Date().toISOString(),
      });
    }

    // --- Infinity Stream (SSE) ---
    if (path === "/infinity/stream") return infinityStream();

    // --- WebSocket ---
    const wsMatch = path.match(/^\/ws\/([^/]+)$/);
    if (wsMatch) {
      if (request.headers.get("Upgrade") !== "websocket") {
        return json({ error: "Expected WebSocket upgrade" }, 426);
      }
      return handleWebSocket(request, wsMatch[1]);
    }

    return json({ error: "Not found", path }, 404);
  },
};
