---
description: how to manage the database
---

# Database Management Workflow

## Database Location
- Primary database: `db/chat.db` (SQLite)
- Backup location: `db/chat.db.backup`

## Backup Database
// turbo
1. Create backup: `cp db/chat.db db/chat.db.backup.$(date +%Y%m%d_%H%M%S)`
2. Verify backup exists: `ls -lh db/chat.db.backup.*`

## Restore Database
1. Stop the application
// turbo
2. Restore from backup: `cp db/chat.db.backup db/chat.db`
3. Restart the application

## Reset Database (Caution!)
1. Backup current database first (see above)
2. Stop the application
// turbo
3. Remove database file: `rm db/chat.db`
4. Restart application (will create fresh database)

## Inspect Database
1. Open SQLite CLI: `sqlite3 db/chat.db`
2. Useful commands:
   - List tables: `.tables`
   - Show schema: `.schema <table_name>`
   - Query data: `SELECT * FROM <table_name> LIMIT 10;`
   - Exit: `.quit`

## Database in Docker
// turbo
1. Access database in running container: `docker-compose exec backend sqlite3 /app/db/chat.db`
2. Copy database from container: `docker cp <container_id>:/app/db/chat.db ./db/chat.db.backup`

## Migration (if needed)
1. Create migration script in `scripts/` directory
2. Run migration: `python scripts/migrate_database.py`
3. Verify migration success

## Notes
- **Always backup before making changes**
- The database file is mounted as a volume in Docker
- Redis is used for caching, not persistent storage
- Check DATABASE_URL in `.env` for configuration
