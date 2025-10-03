"""
Malcolm AI — Main FastAPI entrypoint
- Mounts the core API app from `malcolmai_api.py`
- Provides Infinity Stream (SSE) at /infinity/stream
- Provides a favicon fallback to avoid 404 noise in the console
"""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse, FileResponse, Response
import asyncio
import os

# Import your core FastAPI app (login/optimize/omni/ws/static/root/healthz live there)
from malcolmai_api import app as malcolm_app

# ------------------------------------------------------------------------------
# Primary wrapper app
# ------------------------------------------------------------------------------
main_app = FastAPI(title="Malcolm AI — Main")

# Mount the entire Malcolm API at the root
# (All routes defined in malcolmai_api.py remain available at their same paths)
main_app.mount("", malcolm_app)


# ------------------------------------------------------------------------------
# Infinity Stream (Server-Sent Events)
# ------------------------------------------------------------------------------
async def _infinity_event_stream():
    """
    Simple heartbeat stream; replace the message source with any async generator
    that yields 'data: <payload>\\n\\n' lines.
    """
    counter = 0
    # First, suggest the client retry delay (optional)
    yield "retry: 3000\n\n"
    while True:
        counter += 1
        # The 'data: ...' format is required by SSE
        yield f"data: Infinity transmission #{counter}\n\n"
        await asyncio.sleep(2)

@main_app.get("/infinity/stream")
async def infinity_stream():
    """
    Live Infinity Stream endpoint used by the landing page.
    """
    # Helpful headers for SSE
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        # CORS can be set at proxy level; add here if you need cross-origin use:
        # "Access-Control-Allow-Origin": "*",
    }
    return StreamingResponse(
        _infinity_event_stream(),
        media_type="text/event-stream",
        headers=headers,
    )

# ------------------------
# Hypercosmic Theatre Network (HTN)
# ------------------------
from fastapi.responses import HTMLResponse

@main_app.get("/htn", response_class=HTMLResponse)
async def hypercosmic_theatre():
    """Serve the Hypercosmic Theatre Network livestream page"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Hypercosmic Theatre Network</title>
      <style>
        body {
          margin: 0;
          background-color: black;
          display: flex;
          justify-content: center;
          align-items: center;
          height: 100vh;
        }
        iframe {
          border: none;
        }
      </style>
    </head>
    <body>
      <iframe width="100%" height="100%"
        src="rtmp://a.rtmp.youtube.com/live2"
        title="Hypercosmic Theatre Network"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        allowfullscreen>
      </iframe>
    </body>
    </html>
    """

# ------------------------------------------------------------------------------
# Favicon handler (prevents console 404 if you don't ship a real favicon)
# ------------------------------------------------------------------------------
@main_app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """
    Serves /static/favicon.ico if present; otherwise returns 204 (no content).
    """
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    ico_path = os.path.join(static_dir, "favicon.ico")
    if os.path.exists(ico_path):
        return FileResponse(ico_path)
    return Response(status_code=204)


# ------------------------------------------------------------------------------
# Local dev entrypoint
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    # Run the *main* app so /infinity/stream is available
    uvicorn.run("main:main_app", host="0.0.0.0", port=8000, reload=True)
