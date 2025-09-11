# Use a slim Python base
FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set workdir
WORKDIR /app

# System deps (optional but useful)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Copy and install deps first (leverages Docker layer cache)
COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy app code
COPY . .

# Expose Fly internal port
EXPOSE 8080

# Start FastAPI (main:main_app) on 0.0.0.0:8080 — JSON exec form is important
CMD ["uvicorn", "main:main_app", "--host", "0.0.0.0", "--port", "8080"]
