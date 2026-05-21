#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Vunoh AI — One-command local setup
# Run from the project root:  bash setup.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}▶${NC} $1"; }
warn()    { echo -e "${YELLOW}⚠${NC}  $1"; }
error()   { echo -e "${RED}✗${NC} $1"; exit 1; }

# ── 0. Sanity checks ──────────────────────────────────────────────────────────
command -v python3 >/dev/null 2>&1 || error "Python 3 not found. Install Python 3.11+."
command -v redis-cli >/dev/null 2>&1 || warn "redis-cli not found — make sure Redis is running before starting Celery."

# ── 1. Python virtual environment ─────────────────────────────────────────────
info "Creating virtual environment…"
python3 -m venv .venv
source .venv/bin/activate

info "Installing Python dependencies…"
pip install -q -r backend/requirements.txt

# ── 2. Environment file ───────────────────────────────────────────────────────
if [ ! -f backend/.env ]; then
  info "Creating backend/.env from .env.example…"
  cp backend/.env.example backend/.env
  echo ""
  warn "backend/.env created. Open it and fill in your API keys before starting the app:"
  warn "  GROQ_API_KEY    → https://console.groq.com"
  warn "  GEMINI_API_KEY  → https://aistudio.google.com"
  warn "  (Twilio and Gmail are optional — only needed for actual message sending)"
  echo ""
else
  info "backend/.env already exists — skipping."
fi

# ── 3. Database ───────────────────────────────────────────────────────────────
info "Setting up PostgreSQL database…"

# Detect Postgres port (Postgres.app uses 5433, Homebrew uses 5432)
PG_PORT=${DB_PORT:-5432}
PG_SUPERUSER=${PGUSER:-postgres}

# Try to create user and database (errors are suppressed if they already exist)
psql -U "$PG_SUPERUSER" -p "$PG_PORT" -c "CREATE USER vunoh_user WITH PASSWORD 'vunoh_pass';" 2>/dev/null || true
psql -U "$PG_SUPERUSER" -p "$PG_PORT" -c "CREATE DATABASE vunoh OWNER vunoh_user;" 2>/dev/null || true

info "Running Django migrations…"
cd backend
python manage.py migrate --run-syncdb -v 0

info "Loading seed data (5 sample tasks with steps, messages, entities)…"
python manage.py loaddata fixtures/seed.json
cd ..

# ── 4. Done ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}✓ Setup complete.${NC}"
echo ""
echo "Start the app with three terminals:"
echo ""
echo -e "  ${YELLOW}Terminal 1 — Django API${NC}"
echo "    source .venv/bin/activate && cd backend && python manage.py runserver"
echo ""
echo -e "  ${YELLOW}Terminal 2 — Celery worker${NC}"
echo "    source .venv/bin/activate && cd backend && celery -A config.celery worker --loglevel=info"
echo ""
echo -e "  ${YELLOW}Terminal 3 — Frontend${NC}"
echo "    Open frontend/index.html with Live Server (VS Code extension)"
echo "    or: npx live-server frontend --port=5500"
echo ""
echo "Then open: http://localhost:5500"
echo ""
echo -e "${YELLOW}Note (Postgres.app users):${NC}"
echo "  If your Postgres runs on port 5433, set DB_PORT=5433 in backend/.env"
echo "  and re-run:  cd backend && python manage.py migrate"
