from fastapi import FastAPI, Request, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from typing import Dict
import time
import os
import subprocess
import sys

# === CONFIG ===
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 3600

app = FastAPI()

# Auto-start daemon on startup
@app.on_event("startup")
async def start_daemon():
    daemon_path = os.path.join(os.path.dirname(__file__), "malcolmai_daemon.py")
    if os.path.exists(daemon_path):
        subprocess.Popen([sys.executable, daemon_path])

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("static/index.html")

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

security = HTTPBearer()

# === AUTH UTILITIES ===
def create_access_token(data: dict, expires_delta: int = ACCESS_TOKEN_EXPIRE_SECONDS):
    to_encode = data.copy()
    expire = time.time() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise Exception("Invalid or expired token")

# === AUTH ENDPOINT ===
@app.post("/login")
async def login(request: Request):
    data = await request.json()
    if data.get("username") == "admin" and data.get("password") == "password":
        token = create_access_token({"sub": "admin"})
        return {"access_token": token}
    return {"error": "Invalid credentials"}

# === OPTIMIZER ENDPOINT ===
@app.post("/optimize")
async def optimize(request: Request, user: dict = Depends(verify_token)):
    data = await request.json()
    metrics = data.get("data", {})
    actions = []

    if metrics.get("cpu_percent", 0) > 80:
        actions.append({"type": "clear_cache"})
    if metrics.get("memory", {}).get("percent", 0) > 85:
        actions.append({"type": "cleanup_tmp"})
    if metrics.get("disk", {}).get("percent", 0) > 90:
        actions.append({"type": "archive_old_logs"})

    if not actions:
        actions.append({"type": "noop", "detail": "System stable"})

    return JSONResponse(content={"actions": actions})

# === OMNI COMMAND ENDPOINT ===
@app.post("/omni/command")
async def omni_command(request: Request, user: dict = Depends(verify_token)):
    data = await request.json()
    return {"received_command": data.get("command", "ping"), "status": "executed"}

# === WEBSOCKETS ===
clients: Dict[str, WebSocket] = {}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    clients[client_id] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message from {client_id}: {data}")
    except WebSocketDisconnect:
        del clients[client_id]
