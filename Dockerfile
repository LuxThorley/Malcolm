# Use official lightweight Python image
<<<<<<< HEAD
FROM python:3.10-slim
=======
FROM python:3.8.1-slim
>>>>>>> 533ec5cfe1dd892136685d35183546bec105e974

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose port (Fly.io maps to $PORT automatically)
EXPOSE 8080

# Environment variable for Flask
ENV PORT=8080

# Start the app with Gunicorn + Eventlet
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "main:app", "-b", "0.0.0.0:8080"]
