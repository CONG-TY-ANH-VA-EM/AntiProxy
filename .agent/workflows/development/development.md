---
description: how to start the development server
---

# Development Server Workflow

## Frontend (Next.js)
1. Install dependencies if needed: `npm install`
2. Start the Next.js development server: `npm run dev`
3. Access the frontend at `http://localhost:3000`

## Backend (Python/FastAPI)
1. Ensure Python virtual environment is activated
2. Install Python dependencies: `pip install -r requirements.txt`
3. Start the FastAPI server: `python src/api_server.py` or `uvicorn src.api_server:app --reload`
4. Backend API available at `http://localhost:8000`

## Full Stack with Docker
// turbo
1. Start all services: `docker-compose up -d`
2. View logs: `docker-compose logs -f`
3. Stop services: `docker-compose down`

## Notes
- The frontend proxies API requests to the backend
- Check `.env` file for configuration
- Redis and other dependencies are managed via Docker Compose
