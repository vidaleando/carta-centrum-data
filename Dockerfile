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

# The build output will be in frontend/build (or frontend/dist depending on your config)
# We assume standard 'npm run build' output is in 'build' folder for this example. 
# If your svelte-kit/vite config outputs to 'dist', change the path below accordingly.

# 5. Final Setup
WORKDIR /app
# Move built static files to a known location or serve directly from frontend/build
# Our main.py will be configured to serve './frontend/build'

EXPOSE 8000

# Start the backend (which now also serves static files)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

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