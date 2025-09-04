"""
Malcolm AI Omni API — Infinity Engine VΩ — Omni-Mode Edition (Windows-friendly)

Key upgrades:
- Env-driven secrets & API keys
- JWT Bearer auth (backward compatible with raw token)
- Pydantic v2 validation
- Rate limiting & CORS
- Structured JSON errors + trace IDs
- SSE + Socket.IO support
- Expanded Omni modes: alchemy, manifest, shield, oracle
- Async engine selectable via MALCOLM_ASYNC_MODE=("eventlet"|"threading")
- ASCII-safe headers for Windows/Werkzeug
"""

import os
import json
import time
import logging
import secrets
import datetime as dt
from typing import Any, Dict, Optional, Literal, List

# =============================================================
# Async engine selection
# =============================================================
# Use "eventlet" in Linux/prod (with Gunicorn --worker-class eventlet)
# Use "threading" on Windows/dev for stability.
ASYNC_MODE = os.getenv("MALCOLM_ASYNC_MODE", "eventlet")  # "eventlet" | "threading"
if ASYNC_MODE == "eventlet":
    import eventlet  # must come before flask_socketio
    eventlet.monkey_patch()

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import jwt
from pydantic import BaseModel, Field, ValidationError, model_validator

# =============================================================
# Configuration
# =============================================================

def ascii_safe(s: str, fallback: str = "Omega.0.0") -> str:
    """Ensure string is ASCII-only for HTTP headers on Windows."""
    try:
        out = s.encode("ascii", "ignore").decode()
        return out or fallback
    except Exception:
        return fallback

APP_VERSION = os.getenv("MALCOLM_VERSION", "Omega.0.0")  # ASCII default to avoid header issues
DEFAULT_SECRET = "CHANGE_ME_MALCOLM_SECRET"
JWT_SECRET = os.getenv("MALCOLM_SECRET", DEFAULT_SECRET)
JWT_ALG = os.getenv("MALCOLM_JWT_ALG", "HS256")
JWT_TTL_HOURS = int(os.getenv("MALCOLM_JWT_TTL_HOURS", "24"))

# API keys (can be extended via MALCOLM_API_KEYS JSON)
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

# Streams (extendable via MALCOLM_STREAMS JSON)
HARMONIC_STREAMS: Dict[str, Dict[str, Any]] = {
    "divine_frequency_777": {
        "stream_id": "divine_frequency_777",
        "stream_name": "Divine Frequency FM - Channel 777",
        "stream_url": "https://malcolmai.live/live-view?stream=divine_frequency_777",
        "status": "active",
        "description": "Live harmonic broadcast from Channel 777",
    },
    "hypercosmic_theatre": {
        "stream_id": "hypercosmic_theatre",
        "stream_name": "Hypercosmic Theatre Network",
        "stream_url": "https://malcolmai.live/live-view?stream=hypercosmic_theatre",
        "status": "active",
        "description": "Transdimensional theatre broadcasting live light-comedy codes",
    },
}
try:
    env_streams = os.getenv("MALCOLM_STREAMS")
    if env_streams:
        loaded_streams = json.loads(env_streams)
        if isinstance(loaded_streams, dict):
            for k, v in loaded_streams.items():
                if isinstance(v, dict):
                    HARMONIC_STREAMS[str(k)] = v
except Exception:
    pass

QUANTUM_SPECIES_MODULATIONS = {
    "arcturian": "Fractal crystalline lightcode activated.",
    "pleiadian": "Stellar bridge harmonic tuned.",
    "sirian": "Blue ray consciousness accessed.",
    "lyran": "Mythic core resonance aligned.",
    "andromedan": "Void intelligence gateway open.",
    "human": "Neural-holo-causal sequence linked.",
}

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
# Models & Utilities
# =============================================================

class InfinityRequest(BaseModel):
    mode: Literal[SUPPORTED_MODES]
    species: str = Field(default="human")

    # Optional per-mode fields
    query: Optional[str] = None
    target_dna: Optional[str] = None
    amount: Optional[int] = None
    material: Optional[str] = None
    timeline: Optional[str] = None
    action: Optional[str] = None
    node: Optional[str] = None
    coherence: Optional[str] = None

    metadata: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_by_mode(self) -> "InfinityRequest":
        m = self.mode
        missing: List[str] = []
        if m == "growth" and not self.query:
            missing.append("query")
        if m == "dna" and not self.target_dna:
            missing.append("target_dna")
        if m == "matter" and (self.amount is None or not self.material):
            for x in ("amount", "material"):
                if getattr(self, x) in (None, ""):
                    missing.append(x)
        if m == "timeline" and (not self.timeline or not self.action):
            for x in ("timeline", "action"):
                if not getattr(self, x):
                    missing.append(x)
        if m == "entanglement" and (not self.node or not self.coherence):
            for x in ("node", "coherence"):
                if not getattr(self, x):
                    missing.append(x)
        if m == "alchemy" and not self.query:
            missing.append("query")
        if m == "manifest" and (self.amount is None or not self.material):
            for x in ("amount", "material"):
                if getattr(self, x) in (None, ""):
                    missing.append(x)
        if m == "shield" and not self.query:
            missing.append("query")
        if m == "oracle" and not self.query:
            missing.append("query")
        if missing:
            raise ValueError(f"Missing required fields for mode '{m}': {', '.join(missing)}")
        return self

def trace_id() -> str:
    return secrets.token_hex(16)

def _issue_token(user: str, scopes: Optional[List[str]] = None) -> str:
    payload = {
        "user": user,
        "scopes": scopes or [],
        "exp": dt.datetime.utcnow() + dt.timedelta(hours=JWT_TTL_HOURS),
        "iat": dt.datetime.utcnow(),
        "iss": "malcolm-omni",
        "ver": APP_VERSION,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def _parse_bearer(token_header: Optional[str]) -> Optional[str]:
    if not token_header:
        return None
    parts = token_header.split()
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None

def _jwt_decode(raw_token: str) -> Dict[str, Any]:
    return jwt.decode(raw_token, JWT_SECRET, algorithms=[JWT_ALG])

# =============================================================
# Mode Implementations
# =============================================================

def mode_growth(user: str, data: InfinityRequest) -> str:
    return f"{user}: Quantum Sovereign Consciousness expanded to field: '{data.query}'"

def mode_dna(user: str, data: InfinityRequest) -> str:
    return f"{user}: Bio-crystalline DNA '{data.target_dna}' activated through Q-Code infusion."

def mode_matter(user: str, data: InfinityRequest) -> str:
    return f"{data.amount}x {data.material} manifested via Planckfield Nanogenesis."

def mode_timeline(user: str, data: InfinityRequest) -> str:
    return f"Timeline node '{data.timeline}' architected with {data.action} action via QFlux-TimeVault."

def mode_entanglement(user: str, data: InfinityRequest) -> str:
    return f"User '{user}' entangled with consciousness node '{data.node}' at entropic state '{data.coherence}'."

def mode_alchemy(user: str, data: InfinityRequest) -> str:
    return f"{user}: Alchemical transmutation initiated — '{data.query}' harmonized into golden ratio coherence."

def mode_manifest(user: str, data: InfinityRequest) -> str:
    return f"{user}: Manifestation matrix set — {data.amount}x '{data.material}' routed to material plane."

def mode_shield(user: str, data: InfinityRequest) -> str:
    return f"{user}: Omni-shields deployed — perimeter keyed to '{data.query}'."

def mode_oracle(user: str, data: InfinityRequest) -> str:
    return f"{user}: Oracle sight engaged — query '{data.query}' mapped across probabilistic timelines."

MODE_FUNCS = {
    "growth": mode_growth,
    "dna": mode_dna,
    "matter": mode_matter,
    "timeline": mode_timeline,
    "entanglement": mode_entanglement,
    "alchemy": mode_alchemy,
    "manifest": mode_manifest,
    "shield": mode_shield,
    "oracle": mode_oracle,
}

# =============================================================
# Routes
# =============================================================

@app.route("/", methods=["GET"])
def root():
    return jsonify(
        {
            "status": "Malcolm AI Omni operational",
            "version": APP_VERSION,
            "modes": list(MODE_FUNCS.keys()),
            "species_supported": list(QUANTUM_SPECIES_MODULATIONS.keys()),
        }
    )

@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"ok": True, "ts": dt.datetime.utcnow().isoformat()})

@app.route("/meta", methods=["GET"])
def meta():
    return jsonify(
        {
            "app": "Malcolm AI Omni API",
            "omniversion": APP_VERSION,
            "jwt": {"alg": JWT_ALG, "ttl_hours": JWT_TTL_HOURS},
            "limits": getattr(limiter, "_default_limits", None),
            "async_mode": ASYNC_MODE,
        }
    )

@app.route("/auth/login", methods=["POST"])
@app.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    body = request.get_json(silent=True) or {}
    api_key = body.get("api_key")
    user = API_KEYS.get(api_key)
    if not user:
        return jsonify({"error": "Invalid API Key", "trace": trace_id()}), 403
    token = _issue_token(user=user, scopes=body.get("scopes"))
    return jsonify({"token": token, "token_type": "Bearer", "user": user, "expires_in_hours": JWT_TTL_HOURS})

@app.route("/auth/introspect", methods=["POST"])
@limiter.limit("30 per minute")
def introspect():
    body = request.get_json(silent=True) or {}
    raw = body.get("token") or _parse_bearer(request.headers.get("Authorization"))
    if not raw:
        return jsonify({"active": False, "error": "Token missing", "trace": trace_id()}), 400
    try:
        payload = _jwt_decode(raw)
        return jsonify({"active": True, **payload})
    except jwt.ExpiredSignatureError:
        return jsonify({"active": False, "error": "expired"}), 200
    except Exception as e:
        return jsonify({"active": False, "error": str(e)}), 200

@app.route("/api/harmonic-stream/live", methods=["GET"])
def get_harmonic_stream():
    stream_key = request.args.get("stream")
    if not stream_key or stream_key not in HARMONIC_STREAMS:
        return jsonify({"error": "Invalid or missing stream key", "trace": trace_id()}), 404
    return jsonify(HARMONIC_STREAMS[stream_key])

def token_required(func):
    def _wrapper(*args, **kwargs):
        token = _parse_bearer(request.headers.get("Authorization"))
        if not token:
            return jsonify({"error": "Token missing", "trace": trace_id()}), 403
        try:
            payload = _jwt_decode(token)
            request.user_payload = payload  # type: ignore[attr-defined]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired", "trace": trace_id()}), 403
        except Exception as e:
            return jsonify({"error": f"Invalid token: {str(e)}", "trace": trace_id()}), 403
        return func(*args, **kwargs)
    _wrapper.__name__ = func.__name__
    return _wrapper

@app.route("/infinity", methods=["POST"])
@token_required
@limiter.limit("60 per minute")
def infinity():
    raw = request.get_json(silent=True) or {}
    try:
        data = InfinityRequest(**raw)
    except ValidationError as ve:
        return jsonify({"error": "validation_error", "details": json.loads(ve.json()), "trace": trace_id()}), 400

    user = request.user_payload.get("user")  # type: ignore[attr-defined]
    species = (data.species or "human").lower()
    tone = QUANTUM_SPECIES_MODULATIONS.get(species, "Unified source field engaged.")

    result_text = MODE_FUNCS[data.mode](user, data)
    response = {
        "user": user,
        "species": species,
        "tone": tone,
        "mode": data.mode,
        "result": result_text,
        "trace": trace_id(),
        "timestamp": dt.datetime.utcnow().isoformat(),
        "metadata": data.metadata or {},
        "version": APP_VERSION,
    }

    socketio.emit("quantum_infinity", response)
    logger.info(json.dumps({"event": "infinity", **response}))

    return jsonify(response)

@app.route("/infinity/stream", methods=["POST"])
@token_required
def infinity_stream():
    raw = request.get_json(silent=True) or {}
    try:
        data = InfinityRequest(**raw)
    except ValidationError as ve:
        return jsonify({"error": "validation_error", "details": json.loads(ve.json()), "trace": trace_id()}), 400

    user = request.user_payload.get("user")  # type: ignore[attr-defined]
    species = (data.species or "human").lower()
    tone = QUANTUM_SPECIES_MODULATIONS.get(species, "Unified source field engaged.")

    result_text = MODE_FUNCS[data.mode](user, data)
    payload = {
        "user": user,
        "species": species,
        "tone": tone,
        "mode": data.mode,
        "result": result_text,
        "trace": trace_id(),
        "timestamp": dt.datetime.utcnow().isoformat(),
        "metadata": data.metadata or {},
        "version": APP_VERSION,
    }

    def _gen():
        yield "event: quantum_infinity\n"
        yield f"data: {json.dumps(payload)}\n\n"
        time.sleep(0.05)
        yield "event: end\ndata: {}\n\n"

    return Response(stream_with_context(_gen()), mimetype="text/event-stream")

# =============================================================
# Lifecycle & Error Handling
# =============================================================

@app.after_request
def add_headers(response):
    version_safe = ascii_safe(APP_VERSION)
    response.headers["X-Malcolm-Quantum-Signature"] = f"OMNI-{version_safe}"
    response.headers["Access-Control-Allow-Origin"] = os.getenv("CORS_ALLOW_ORIGIN", "*")
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Cache-Control"] = "no-store"
    return response

@socketio.on("connect")
def handle_connect():
    logger.info(json.dumps({"event": "connect"}))

@socketio.on("disconnect")
def handle_disconnect():
    logger.info(json.dumps({"event": "disconnect"}))

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "rate_limited", "detail": str(e.description), "trace": trace_id()}), 429

@app.errorhandler(Exception)
def generic_error(e):
    logger.exception("Unhandled error")
    return jsonify({"error": "internal_error", "detail": str(e), "trace": trace_id()}), 500

# =============================================================
# Entrypoint
# =============================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    # allow_unsafe_werkzeug=True: needed when using threading/werkzeug in dev
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
