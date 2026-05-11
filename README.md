# PWA Map Application

A Progressive Web Application that displays geographical data from a PostGIS database on an interactive map using MapLibre GL JS. The frontend is built with Svelte, and the backend uses Python with FastAPI.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │     │    Backend      │     │   Database      │
│   (Svelte)      │────▶│   (FastAPI)     │────▶│   (PostGIS)     │
│   MapLibre GL   │◀────│   Python        │◀────│   PostgreSQL    │
│   PWA           │     │   REST API      │     │   + PostGIS     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Tech Stack

### Frontend
- **Svelte** - Reactive frontend framework
- **MapLibre GL JS** - Open-source map library
- **Vite** - Build tool and dev server
- **PWA** - Progressive Web App features (offline support, installable)

### Backend
- **Python** - Programming language
- **FastAPI** - Modern, fast web framework
- **asyncpg** - Async PostgreSQL client
- **PostGIS** - Spatial database extender

### Database
- **PostgreSQL** - Relational database
- **PostGIS** - Geographic objects support

## Project Structure

```
/workspace
├── frontend/              # Svelte frontend application
│   ├── public/
│   │   ├── manifest.json  # PWA manifest
│   │   ├── sw.js          # Service worker
│   │   └── favicon.svg
│   ├── src/
│   │   ├── App.svelte     # Main application component
│   │   └── main.js        # Entry point
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── backend/               # Python FastAPI backend
│   ├── main.py            # Main application
│   ├── requirements.txt   # Python dependencies
│   ├── .env.example       # Environment variables template
│   └── database_setup.sql # Database schema
│
└── README.md
```

## Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- PostgreSQL 12+ with PostGIS extension
- Git
- **Docker Desktop** (for macOS users - optional but recommended)

## Quick Start for macOS Users

### Option 1: Using Docker (Recommended for macOS)

See the detailed guide in [`MACOS_DOCKER_SETUP.md`](./MACOS_DOCKER_SETUP.md) for complete instructions on running this application with Docker on macOS.

**Quick steps:**

1. Install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
2. Configure file sharing in Docker Desktop (Settings → Resources → File Sharing)
3. Run the setup script:
   ```bash
   chmod +x setup_docker_macos.sh
   ./setup_docker_macos.sh
   ```
4. Or manually:
   ```bash
   docker compose up -d --build
   ```

Access the app at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000

### Option 2: Native Installation

Follow the standard installation steps below.

---

## Standard Installation (All Platforms)

## Installation

### 1. Clone and Setup

```bash
cd /workspace
```

### 2. Database Setup

1. Install PostgreSQL with PostGIS:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib postgis
   
   # Or use Docker
   docker run -d --name postgres-gis \
     -e POSTGRES_PASSWORD=postgres \
     -p 5432:5432 \
     postgis/postgis:15-3.3
   ```

2. Create database and run setup script:
   ```bash
   createdb gisdb
   psql -d gisdb -f backend/database_setup.sql
   ```

3. Configure environment variables:
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your database credentials
   ```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the backend server
python main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The frontend will be available at `http://localhost:3000`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check |
| GET | `/api/geojson` | Get all geographical data as GeoJSON |
| POST | `/api/geojson` | Create new geographical feature |

### Example API Usage

```bash
# Get all features
curl http://localhost:8000/api/geojson

# Get features with limit
curl "http://localhost:8000/api/geojson?limit=10"

# Create new feature
curl -X POST http://localhost:8000/api/geojson \
  -H "Content-Type: application/json" \
  -d '{
    "type": "Feature",
    "geometry": {
      "type": "Point",
      "coordinates": [-74.0060, 40.7128]
    },
    "properties": {
      "name": "New Location",
      "description": "A new point",
      "category": "poi"
    }
  }'
```

## PWA Features

This application includes:

- **Offline Support**: Service worker caches assets for offline use
- **Installable**: Can be installed on mobile/desktop devices
- **Responsive**: Works on all screen sizes
- **Fast**: Optimized loading and rendering

To test PWA features:
1. Build the frontend: `npm run build`
2. Preview: `npm run preview`
3. Open in browser and check "Add to Home Screen" option

## Customization

### Adding Your Own Data

1. Modify `backend/database_setup.sql` to match your schema
2. Update the query in `backend/main.py` to fetch your data
3. Adjust the map layers in `frontend/src/App.svelte` to style your data

### Map Styling

Edit the MapLibre style in `App.svelte`:
```javascript
map = new Map({
  container: 'map',
  style: 'your-style-url',  // Use your own MapLibre style
  center: [longitude, latitude],
  zoom: zoom_level
});
```

## Development Tips

### Hot Reload
Both frontend and backend support hot reload during development:
- Frontend: Automatic with Vite
- Backend: Run with `uvicorn main:app --reload`

### Debugging
- Frontend: Use browser DevTools
- Backend: Check console logs or add logging statements
- Database: Use pgAdmin or psql to inspect data

### Testing PWA
Use Chrome DevTools:
1. Open Application tab
2. Check Service Workers
3. Test offline mode
4. Validate manifest

## Production Deployment

### Frontend
```bash
cd frontend
npm run build
# Deploy dist/ folder to your web server
```

### Backend
```bash
cd backend
# Use a production ASGI server like Gunicorn
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Environment Variables for Production
Set these in your production environment:
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`

## Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running
- Check credentials in `.env`
- Ensure PostGIS extension is enabled

### Map Not Loading
- Check browser console for errors
- Verify API is running and accessible
- Check CORS settings if using different ports

### PWA Not Working
- Ensure HTTPS (required for service workers in production)
- Check service worker registration in browser DevTools
- Validate manifest.json

## License

MIT License - feel free to use this project for your needs!

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
