"""
Malcolm AI Omni API — Infinity Engine VΩ — Omni-Mode Edition
-----------------------------------------------------------
Features:
- JWT Bearer authentication (with backward-compatible raw token support)
- Pydantic v2 request validation
- Rate limiting & CORS
- Structured JSON error responses with trace IDs
- SSE & Socket.IO streaming support
- Expanded Omni modes: growth, dna, matter, timeline, entanglement, alchemy, manifest, shield, oracle
- Hypercosmic Theatre iframe route
- Client-side Optimizer integration endpoint
- Async mode selectable via MALCOLM_ASYNC_MODE=("eventlet"|"threading")
- Safe for both Windows development & Linux/Fly.io deployment
"""

import os
import json
import time
import logging
import secrets
import datetime as dt
from typing import Any, Dict, Optional, Literal, List

# =============================================================
# Async engine selection (must happen before Flask imports)
# =============================================================
ASYNC_MODE = os.getenv("MALCOLM_ASYNC_MODE", "eventlet")  # "eventlet" | "threading"
if ASYNC_MODE == "eventlet":
    import eventlet
    eventlet.monkey_patch()

from flask import (
    Flask,
    request,
    jsonify,
    Response,
    stream_with_context,
    render_template_string,
)
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import jwt
from pydantic import BaseModel, Field, ValidationError, model_validator

# =============================================================
# Configuration & Helpers
# =============================================================

def ascii_safe(s: str, fallback: str = "Omega.0.0") -> str:
    """Ensure string is ASCII-only for HTTP headers on Windows."""
    try:
        out = s.encode("ascii", "ignore").decode()
        return out or fallback
    except Exception:
        return fallback

APP_VERSION = os.getenv("MALCOLM_VERSION", "Omega.0.0")
JWT_SECRET = os.getenv("MALCOLM_SECRET", "CHANGE_ME_MALCOLM_SECRET")
JWT_ALG = os.getenv("MALCOLM_JWT_ALG", "HS256")
JWT_TTL_HOURS = int(os.getenv("MALCOLM_JWT_TTL_HOURS", "24"))

API_KEYS: Dict[str, str] = {
    "KEY_COSMIC_ALPHA": "UserAlpha",
    "KEY_OMEGA_ROOT": "OmegaMaster",
    "KEY_UNITY_SOURCE": "CoreNode",
}
try:
    env_keys = os.getenv("MALCOLM_API_KEYS")
    if env_keys:
        loaded = json.loads(env_keys)
        if isinstance(loaded, dict):
            API_KEYS.update({str(k): str(v) for k, v in loaded.items()})
except Exception:
    pass

SUPPORTED_MODES = (
    "growth",
    "dna",
    "matter",
    "timeline",
    "entanglement",
    "alchemy",
    "manifest",
    "shield",
    "oracle",
)

# =============================================================
# App + Extensions
# =============================================================

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET", os.urandom(32).hex())

socketio = SocketIO(app, cors_allowed_origins="*", async_mode=ASYNC_MODE)
CORS(app, resources={r"/*": {"origins": os.getenv("CORS_ORIGINS", "*")}})
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per hour", "20 per minute"])

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("malcolm.omni")

# =============================================================
# Models
# =============================================================

class InfinityRequest(BaseModel):
    mode: Literal[SUPPORTED_MODES]
    payload: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_payload(self) -> "InfinityRequest":
        if not isinstance(self.payload, dict):
            raise ValueError("Payload must be a dictionary")
        return self

# =============================================================
# Token Utilities
# =============================================================

def _issue_token(user: str, scopes: Optional[List[str]] = None) -> str:
    payload = {
        "sub": user,
        "scopes": scopes or [],
        "iat": dt.datetime.utcnow(),
        "exp": dt.datetime.utcnow() + dt.timedelta(hours=JWT_TTL_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def _require_auth() -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    else:
        token = auth_header or request.args.get("token", "")
    if not token:
        return "unauthorized"
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return "authorized"
    except jwt.PyJWTError:
        return "unauthorized"

# =============================================================
# Mode Handlers
# =============================================================

def process_mode(mode: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if mode == "growth":
        return {"insight": "You are expanding into new dimensions."}
    if mode == "dna":
        return {"insight": "Genetic archetypes resonate with evolution."}
    if mode == "matter":
        return {"insight": "Matter reconfigures in alignment with will."}
    if mode == "timeline":
        return {"insight": "Threads of destiny converge in your awareness."}
    if mode == "entanglement":
        return {"insight": "Hidden patterns of synchronicity emerge."}
    if mode == "alchemy":
        return {"insight": "Inputs transform into symbolic gold."}
    if mode == "manifest":
        return {"insight": "Intent projects into tangible reality."}
    if mode == "shield":
        return {"insight": "Protective layers of energy are activated."}
    if mode == "oracle":
        return {"insight": "Archetypal intelligence reveals guidance."}
    return {"insight": "Mode not recognized."}

# =============================================================
# Routes
# =============================================================

@app.route("/")
def index_root():
    return jsonify({
        "message": "Welcome to Malcolm AI Omni API — Infinity Engine",
        "version": APP_VERSION,
        "modes": SUPPORTED_MODES,
        "docs": "Visit /meta or the landing page for instructions."
    })

@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok", "version": APP_VERSION})

@app.route("/meta")
def meta():
    return jsonify({
        "name": "Malcolm AI Omni API",
        "version": APP_VERSION,
        "modes": SUPPORTED_MODES,
        "async_mode": ASYNC_MODE,
    })

@app.route("/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    api_key = data.get("api_key")
    if not api_key or api_key not in API_KEYS:
        return jsonify({"error": "Invalid API key"}), 401
    user = API_KEYS[api_key]
    token = _issue_token(user)
    return jsonify({"token": token})

@app.route("/infinity", methods=["POST"])
def infinity():
    if _require_auth() != "authorized":
        return jsonify({"error": "Unauthorized"}), 401
    try:
        req = InfinityRequest(**(request.json or {}))
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400
    result = process_mode(req.mode, req.payload)
    return jsonify({"mode": req.mode, "result": result})

@app.route("/infinity/stream", methods=["POST"])
def infinity_stream():
    if _require_auth() != "authorized":
        return jsonify({"error": "Unauthorized"}), 401
    try:
        req = InfinityRequest(**(request.json or {}))
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    def generate():
        yield "retry: 500\n\n"
        for i in range(3):
            chunk = {"step": i, "insight": f"{req.mode} expansion phase {i}"}
            yield f"data: {json.dumps(chunk)}\n\n"
            time.sleep(1)
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/hypercosmic")
def hypercosmic():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Hypercosmic Theatre Channel</title>
      <style>
        body { margin: 0; background: black; display: flex; justify-content: center; align-items: center; height: 100vh; }
        iframe { border: none; width: 80vw; height: 45vw; max-width: 1280px; max-height: 720px; }
      </style>
    </head>
    <body>
      <iframe width="800" height="450"
        src="https://www.youtube.com/embed/NOtYFwxtflk?autoplay=1"
        title="Hypercosmic Theatre Channel"
        frameborder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        allowfullscreen>
      </iframe>
    </body>
    </html>
    """)

@app.route("/optimize", methods=["POST"])
def optimize():
    data = request.json or {}
    recommendations = []
    if data.get("cores") and int(data["cores"]) < 4:
        recommendations.append("Upgrade your CPU for smoother performance.")
    if data.get("memory") and data["memory"] != "unknown":
        try:
            if float(data["memory"]) < 8:
                recommendations.append("Consider adding more RAM for better multitasking.")
        except:
            pass
    if "connection" in data and "Mbps" in str(data["connection"]):
        try:
            speed = float(data["connection"].split()[0])
            if speed < 10:
                recommendations.append("Your network is slow — consider upgrading your plan.")
        except:
            pass
    if not recommendations:
        recommendations.append("Your system appears well-balanced. No immediate optimisations required.")
    return jsonify({"environment": data, "recommendations": recommendations})

# =============================================================
# Error Handlers
# =============================================================

@app.errorhandler(429)
def rate_limit_handler(e):
    return jsonify({"error": "Rate limit exceeded", "details": str(e)}), 429

@app.errorhandler(500)
def internal_error(e):
    trace_id = secrets.token_hex(8)
    logger.error(f"[trace {trace_id}] {e}")
    return jsonify({"error": "Internal server error", "trace_id": trace_id}), 500

# =============================================================
# Entrypoint
# =============================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
