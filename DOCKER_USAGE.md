# Build and start all services
docker-compose up --build

# Or run in detached mode (background)
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Stop and remove volumes (database data)
docker-compose down -v

# Access database directly
docker-compose exec db psql -U postgres -d gisdb

# Access backend shell
docker-compose exec backend bash

# Access frontend shell
docker-compose exec frontend sh

# Restart a specific service
docker-compose restart backend

# Rebuild a specific service
docker-compose up --build -d frontend

## Quick Start for macOS

### Prerequisites
Make sure you have Docker Desktop installed on your Mac:
1. Download from https://www.docker.com/products/docker-desktop/
2. Install and start Docker Desktop
3. Wait for Docker to be running (whale icon in menu bar)

### Running the Application

1. **Start all services:**
   ```bash
   cd /workspace
   docker-compose up -d --build
   ```

2. **Wait for services to be ready** (about 30-60 seconds for first build)
   ```bash
   docker-compose ps
   ```

3. **Access the application:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

4. **View logs:**
   ```bash
   docker-compose logs -f
   ```

5. **Stop everything:**
   ```bash
   docker-compose down
   ```

### Notes
- The database will persist data in a Docker volume
- All services run in isolated containers
- No need to install Python, Node.js, or PostgreSQL on your Mac
- The app works in DEMO_MODE by default (sample data without database)
