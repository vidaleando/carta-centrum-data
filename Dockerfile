FROM python:3.11-slim

WORKDIR /app

# 1. Install System Dependencies
# - libpq-dev: For Python Postgres drivers
# - nodejs & npm: Required to build the Svelte frontend
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python Dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy Backend Code
COPY backend/ ./backend/

# 4. Build Frontend
COPY frontend/ ./frontend/
WORKDIR /app/frontend
RUN npm ci && npm run build

# Vite writes the build to /app/frontend/build, which the backend serves
# (Settings.frontend_build_dir).

# 5. Final Setup
# Run from backend/ so `app.*`, `importers.*` and `migrations` are importable,
# e.g. `docker run … python -m migrations`.
WORKDIR /app/backend

EXPOSE 8000

# Start the backend (which also serves the frontend)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# FROM python:3.11-slim

# WORKDIR /app

# # Install system dependencies
# RUN apt-get update && apt-get install -y \
#     gcc \
#     libpq-dev \
#     && rm -rf /var/lib/apt/lists/*

# # Copy requirements first for better caching
# COPY requirements.txt .

# # Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy application code
# COPY . .

# EXPOSE 8000

# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]