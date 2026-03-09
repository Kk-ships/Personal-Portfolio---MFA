# Database Migrations with Alembic

This directory contains database migrations managed by Alembic.

## Create a new migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description of changes"

# Create empty migration
alembic revision -m "description of changes"
```

## Apply migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade by one version
alembic upgrade +1

# Downgrade by one version
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

## Migration files

Migrations are stored in `alembic/versions/` with the format:
`YYYYMMDD_HHMM_<revision>_<slug>.py`

## Important Notes

- Migrations run automatically on container startup via `start.sh`
- The script checks for existing columns before adding them to prevent errors
- SQLite requires batch mode for ALTER TABLE operations
- All migrations are idempotent (safe to run multiple times)
