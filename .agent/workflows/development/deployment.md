---
description: how to deploy the application
---

# Deployment Workflow

## Docker Deployment (Recommended)

### Initial Setup
1. Ensure `.env` file is configured with production values
2. Update `docker-compose.yml` with production settings if needed

### Deploy
// turbo
1. Pull latest code: `git pull origin main`
2. Build images: `docker-compose build`
3. Stop existing containers: `docker-compose down`
4. Start new containers: `docker-compose up -d`
5. Verify deployment: `docker-compose ps`
6. Check logs: `docker-compose logs -f`

### Health Check
// turbo
1. Check container status: `docker-compose ps`
2. Test frontend: `curl http://localhost:3000`
3. Test backend API: `curl http://localhost:8000/health` (if health endpoint exists)

## Manual Deployment

### Frontend
1. Build the app: `npm run build`
2. Start production server: `npm start`

### Backend
1. Ensure dependencies installed: `pip install -r requirements.txt`
2. Start FastAPI with production settings: `uvicorn src.api_server:app --host 0.0.0.0 --port 8000`

## Database Migration (if needed)
1. Backup existing database: `cp db/chat.db db/chat.db.backup`
2. Run migrations (if migration system exists)
3. Verify database integrity

## Rollback Procedure
// turbo
1. Stop current containers: `docker-compose down`
2. Checkout previous version: `git checkout <previous-commit>`
3. Rebuild and restart: `docker-compose up -d --build`

## Notes
- Always backup database before deployment
- Monitor logs for errors after deployment
- Verify critical features are working
- Update environment variables as needed for production
