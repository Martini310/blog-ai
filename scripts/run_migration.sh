#!/usr/bin/env bash
# Run Alembic migrations inside the running API container.
# Usage: ./scripts/run_migration.sh "add users table"

set -euo pipefail

MESSAGE="${1:-auto}"
docker compose exec api alembic revision --autogenerate -m "$MESSAGE"
docker compose exec api alembic upgrade head
echo "Migration complete."
