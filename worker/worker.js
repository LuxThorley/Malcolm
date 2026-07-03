/**
 * Malcolm AI Omni API — Infinity Engine VΩ
 * Full-stack Cloudflare Worker (malcolmai-live)
 *
 * Ports the FastAPI backend (malcolmai_api.py + main.py) to Cloudflare Workers
 * and serves the portal frontend at the same origin for seamless integration.
 *
 * Endpoints:
 *   GET  /                 — portal frontend
 *   GET  /healthz          — health check
 *   POST /login            — JWT auth (HS256, WebCrypto)
 *   POST /optimize         — optimizer (Bearer auth)
 *   POST /omni/command     — omni command (Bearer auth)
 *   GET  /modes/status     — Omni-Lattice mode status
 *   GET  /infinity/stream  — live SSE Infinity Stream
 *   GET  /htn              — Hypercosmic Theatre page
 *   GET  /static/logo.png  — Malcolm sigil (proxied from GitHub)
 *   WS   /ws/:client_id    — WebSocket echo channel
 */

import { INDEX_HTML } from "./index_html.js";

// === CONFIG (mirrors FastAPI defaults; override via Worker secrets) ===
const DEFAULTS = {
  SECRET_KEY: "your-secret-key",
  TOKEN_TTL_SECONDS: 3600,
  ADMIN_USER: "admin",
  ADMIN_PASS: "password",
  VERSION: "\u03A9.1.0-cloudflare",
};

const MODES = ["Growth", "DNA", "Matter", "Timeline", "Entanglement", "Alchemy", "Manifest", "Shield", "Oracle", "Unity"];

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

// ---------- JWT (HS256) via WebCrypto ----------
const enc = new TextEncoder();

function b64url(buf) {
  let s = typeof buf === "string" ? btoa(buf) : btoa(String.fromCharCode(...new Uint8Array(buf)));
  return s.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function b64urlDecode(str) {
  str = str.replace(/-/g, "+").replace(/_/g, "/");
  while (str.length % 4) str += "=";
  return atob(str);
}
async function hmacKey(secret) {
  return crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
}
async function createToken(payload, secret, ttl) {
  const header = { alg: "HS256", typ: "JWT" };
  const body = { ...payload, exp: Math.floor(Date.now() / 1000) + ttl };
  const h = b64url(JSON.stringify(header));
  const p = b64url(JSON.stringify(body));
  const key = await hmacKey(secret);
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(`${h}.${p}`));
  return `${h}.${p}.${b64url(sig)}`;
}
async function verifyToken(token, secret) {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const [h, p, s] = parts;
  const key = await hmacKey(secret);
  const sigBytes = Uint8Array.from(b64urlDecode(s), (c) => c.charCodeAt(0));
  const valid = await crypto.subtle.verify("HMAC", key, sigBytes, enc.encode(`${h}.${p}`));
  if (!valid) return null;
  const payload = JSON.parse(b64urlDecode(p));
  if (payload.exp && payload.exp < Math.floor(Date.now() / 1000)) return null;
  return payload;
}
async function requireAuth(request, secret) {
  const auth = request.headers.get("Authorization") || "";
  if (!auth.startsWith("Bearer ")) return null;
  return verifyToken(auth.slice(7), secret);
}

// ---------- Helpers ----------
function json(data, status = 200, extra = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...CORS_HEADERS, ...extra },
  });
}
function html(body, status = 200) {
  return new Response(body, { status, headers: { "Content-Type": "text/html; charset=utf-8", ...CORS_HEADERS } });
}

// ---------- Optimizer logic (ported from malcolmai_api.py) ----------
function runOptimizer(metrics) {
  const actions = [];
  if ((metrics.cpu_percent || 0) > 80) actions.push({ type: "clear_cache" });
  if (((metrics.memory || {}).percent || 0) > 85) actions.push({ type: "cleanup_tmp" });
  if (((metrics.disk || {}).percent || 0) > 90) actions.push({ type: "archive_old_logs" });
  if (actions.length === 0) actions.push({ type: "noop", detail: "System stable" });
  // Enriched full-stack report
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
  let result = `Command executed through the Omni-Lattice.`;
  if (c.includes("shield")) { mode = "Shield"; result = "Multi-layered protection matrix activated. All channels shielded."; }
  else if (c.includes("timeline")) { mode = "Timeline"; result = "Timeline threads opened — past, present and future navigable."; }
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
function infinityStream() {
  const messages = [
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
  ];
  let counter = 0;
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(enc.encode("retry: 3000\n\n"));
      const interval = setInterval(() => {
        counter++;
        const msg = messages[counter % messages.length];
        const coherence = (0.95 + Math.random() * 0.049).toFixed(3);
        controller.enqueue(enc.encode(`data: Infinity transmission #${counter} \u2014 ${msg} [coherence ${coherence}]\n\n`));
        if (counter >= 900) { clearInterval(interval); controller.close(); }
      }, 2000);
    },
  });
  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
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
  return new Response(null, { status: 101, webSocket: client });
}

// ---------- Main router ----------
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    const secret = env.MALCOLM_SECRET || DEFAULTS.SECRET_KEY;

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
        headers: { "Content-Type": "image/png", "Cache-Control": "public, max-age=86400", ...CORS_HEADERS },
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
        version: env.MALCOLM_VERSION || DEFAULTS.VERSION,
        coherence: 0.982,
        colo: (request.cf && request.cf.colo) || "edge",
        timestamp: new Date().toISOString(),
      });
    }

    // --- Auth ---
    if (path === "/login" && request.method === "POST") {
      let data = {};
      try { data = await request.json(); } catch (e) {}
      const user = env.MALCOLM_ADMIN_USER || DEFAULTS.ADMIN_USER;
      const pass = env.MALCOLM_ADMIN_PASS || DEFAULTS.ADMIN_PASS;
      if (data.username === user && data.password === pass) {
        const token = await createToken({ sub: data.username }, secret, DEFAULTS.TOKEN_TTL_SECONDS);
        return json({ access_token: token, token_type: "bearer", expires_in: DEFAULTS.TOKEN_TTL_SECONDS });
      }
      return json({ error: "Invalid credentials" }, 401);
    }

    // --- Optimizer (auth required) ---
    if (path === "/optimize" && request.method === "POST") {
      const user = await requireAuth(request, secret);
      if (!user) return json({ error: "Invalid or expired token" }, 401);
      let data = {};
      try { data = await request.json(); } catch (e) {}
      return json(runOptimizer(data.data || {}));
    }

    // --- Omni command (auth required) ---
    if (path === "/omni/command" && request.method === "POST") {
      const user = await requireAuth(request, secret);
      if (!user) return json({ error: "Invalid or expired token" }, 401);
      let data = {};
      try { data = await request.json(); } catch (e) {}
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
