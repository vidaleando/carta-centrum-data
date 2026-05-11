# Docker Setup Guide for macOS

## Problem: "failed to read dockerfile: no such file or directory"

This error occurs when Docker cannot access your project files. On macOS, Docker Desktop needs explicit permission to access directories.

## Solution Steps

### Option 1: Configure File Sharing in Docker Desktop (Recommended)

1. **Open Docker Desktop** on your Mac
2. Click the **Settings** icon (⚙️) in the top-right corner
3. Go to **Resources** → **File Sharing**
4. Click **+ (Add)** and add your project directory path (e.g., `/Users/yourusername/projects/pwa-map`)
5. Click **Apply & Restart**
6. Try running again:
   ```bash
   docker compose up -d --build
   ```

### Option 2: Move Project to a Shared Directory

Move your project to a directory that's already shared by default:

```bash
# Move to your home directory (usually already shared)
mv /path/to/pwa-map ~/pwa-map
cd ~/pwa-map

# Then run
docker compose up -d --build
```

Common directories that are usually shared by default:
- `/Users/yourusername/`
- `/Volumes/` (external drives, if added)
- `/private/`
- `/tmp/`

### Option 3: Use the Setup Script

Run the included setup script which will diagnose the issue:

```bash
chmod +x setup_docker_macos.sh
./setup_docker_macos.sh
```

## Verify Docker Access

Test if Docker can see your files:

```bash
# This should list your Dockerfiles
docker run --rm -v "$(pwd)":/test alpine ls -la /test/backend/Dockerfile
docker run --rm -v "$(pwd)":/test alpine ls -la /test/frontend/Dockerfile
```

If you get "No such file or directory", Docker doesn't have access to your current directory.

## Alternative: Run Without Docker on macOS

If you prefer not to use Docker, you can run the application directly:

### Backend (Python)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/gisdb"
export DEMO_MODE=true
uvicorn main:app --reload
```

### Frontend (Node.js)
```bash
cd frontend
npm install
npm run dev
```

### Database (PostgreSQL with PostGIS)
Install via Homebrew:
```bash
brew install postgresql postgis
# Then initialize and run the database
```

Or use Docker just for the database:
```bash
docker run -d --name pwa_map_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=gisdb \
  -p 5432:5432 \
  postgis/postgis:15-3.3
```

## Common Issues

### Port Already in Use
If ports 5432, 8000, or 5173 are already in use:
```bash
# Check what's using the port
lsof -i :5432
lsof -i :8000
lsof -i :5173

# Stop conflicting services or change ports in docker-compose.yml
```

### Memory Issues
If Docker runs out of memory:
1. Open Docker Desktop
2. Go to **Settings** → **Resources**
3. Increase memory allocation (recommend 4GB minimum)

### Build Cache Issues
Clear Docker cache and rebuild:
```bash
docker compose build --no-cache
docker compose up -d
```

## Verify Everything is Running

```bash
# Check container status
docker compose ps

# View logs
docker compose logs -f

# Test backend API
curl http://localhost:8000/api/features

# Test frontend
open http://localhost:5173
```

## Cleanup

To stop and remove all containers:
```bash
docker compose down

# To also remove volumes (database data):
docker compose down -v
```
