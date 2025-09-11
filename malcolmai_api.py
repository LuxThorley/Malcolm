from fastapi import FastAPI, Request, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import time

# === CONFIG ===
SECRET_KEY = "your-secret-key"  # Replace with secure value
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 3600


app = FastAPI()

import subprocess
import sys
import os

from fastapi import FastAPI

app = FastAPI()

# Auto-start daemon when API server boots
@app.on_event("startup")
async def start_daemon():
    daemon_path = os.path.join(os.path.dirname(__file__), "malcolmai_daemon.py")
    subprocess.Popen([sys.executable, daemon_path])

@app.get("/")
async def root():
    return {"status": "Malcolm AI API is live", "endpoints": ["/optimize", "/login", "/omni/command", "/ws/{client_id}"]}


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

# === AUTH ENDPOINTS ===
@app.post("/login")
async def login(request: Request):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")

    # Simple hardcoded check (replace with DB or other auth system)
    if username == "admin" and password == "password":
        token = create_access_token({"sub": username})
        return {"access_token": token}
    return {"error": "Invalid credentials"}

# === OPTIMIZER ENDPOINT ===
@app.post("/optimize")
async def optimize(request: Request, user: dict = Depends(verify_token)):
    """
    Receives system metrics from daemon and returns actions.
    """
    data = await request.json()
    metrics = data.get("data", {})
    actions = []

    # Example optimization rules
    if metrics.get("cpu_percent", 0) > 80:
        actions.append({"type": "clear_cache"})
    if metrics.get("memory", {}).get("percent", 0) > 85:
        actions.append({"type": "cleanup_tmp"})
    if metrics.get("disk", {}).get("percent", 0) > 90:
        actions.append({"type": "archive_old_logs"})

    return JSONResponse(content={"actions": actions})

# === OMNI API SAMPLE ENDPOINT ===
@app.post("/omni/command")
async def omni_command(request: Request, user: dict = Depends(verify_token)):
    data = await request.json()
    command = data.get("command", "ping")
    return {"received_command": command, "status": "executed"}

# === REALTIME SOCKETS VIA WEBSOCKETS ===
clients = {}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    clients[client_id] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back or broadcast
            await websocket.send_text(f"Message from {client_id}: {data}")
    except WebSocketDisconnect:
        del clients[client_id]

# === STARTUP ===
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("malcolmai_api:app", host="0.0.0.0", port=8000, reload=True)
