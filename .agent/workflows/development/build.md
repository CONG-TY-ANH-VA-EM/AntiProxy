---
description: how to build for production
---

# Production Build Workflow

## Frontend Build
// turbo
1. Install dependencies: `npm install`
2. Run production build: `npm run build`
3. Test production build locally: `npm start`

## Docker Build
1. Build frontend Docker image: `docker build -t chat-ane-frontend .`
2. Build backend Docker image: `docker build -f Dockerfile.agent -t chat-ane-backend .`

## Full Stack Docker Build
// turbo
1. Build all services: `docker-compose build`
2. Start production containers: `docker-compose up -d`

## Build Verification
1. Check build output in `.next/` directory
2. Verify no build errors in logs
3. Test critical paths (login, chat, streaming)

## Common Issues
- **Build fails with type errors**: Run `npm run lint` to identify TypeScript issues
- **Missing environment variables**: Ensure all required vars are in `.env`
- **Large bundle size**: Check `next.config.mjs` for optimization settings

## Notes
- Production builds are optimized and minified
- Environment variables with `NEXT_PUBLIC_` prefix are embedded at build time
- Backend doesn't require a build step (Python), but dependencies must be installed
