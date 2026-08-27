#!/bin/bash

set -euo pipefail

APP_DIR="/opt/event-simulator"
REPO_URL="https://github.com/scastanoa1/ProyectoDatosE-Commerce.git"
REPO_DIR="/tmp/ProyectoDatosE-Commerce"

MIGRATION_FILE="${REPO_DIR}/data-generators/database/migrations/001_create_database_and_tables.sql"
SEED_FILE="${REPO_DIR}/data-generators/database/seeds/001_seed_ecommerce.sql"

echo "=== PostgreSQL + Event Simulator bootstrap started ==="

# ============================================================
# 1. INSTALAR DEPENDENCIAS DEL SISTEMA
# ============================================================

echo "=== Installing system dependencies ==="

apt-get update

apt-get install -y \
    git \
    python3-venv \
    postgresql \
    postgresql-contrib


# ============================================================
# 2. INICIAR POSTGRESQL
# ============================================================

echo "=== Starting PostgreSQL ==="

systemctl enable postgresql
systemctl start postgresql

# Esperar a que PostgreSQL esté disponible
until sudo -u postgres pg_isready; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done


# ============================================================
# 3. CLONAR REPOSITORIO
# ============================================================

echo "=== Cloning repository ==="

rm -rf "${REPO_DIR}"

git clone --depth 1 "${REPO_URL}" "${REPO_DIR}"


# ============================================================
# 4. VALIDAR SCRIPTS DE BASE DE DATOS
# ============================================================

echo "=== Validating database scripts ==="

if [ ! -f "${MIGRATION_FILE}" ]; then
    echo "ERROR: Migration file not found:"
    echo "${MIGRATION_FILE}"
    exit 1
fi

if [ ! -f "${SEED_FILE}" ]; then
    echo "ERROR: Seed file not found:"
    echo "${SEED_FILE}"
    exit 1
fi


# ============================================================
# 5. CREAR BASE DE DATOS Y TABLAS
# ============================================================

echo "=== Creating database and tables ==="

sudo -u postgres psql \
    -f "${MIGRATION_FILE}"


# ============================================================
# 6. EJECUTAR SEED
# ============================================================

echo "=== Loading ecommerce seed ==="

sudo -u postgres psql \
    -d ecommerce \
    -f "${SEED_FILE}"


# ============================================================
# 7. VALIDAR BASE DE DATOS
# ============================================================

echo "=== Validating database ==="

sudo -u postgres psql \
    -d ecommerce \
    -c "SELECT COUNT(*) AS users FROM users;"

sudo -u postgres psql \
    -d ecommerce \
    -c "SELECT COUNT(*) AS products FROM products;"

sudo -u postgres psql \
    -d ecommerce \
    -c "SELECT COUNT(*) AS orders FROM orders;"


# ============================================================
# 8. PREPARAR EVENT SIMULATOR
# ============================================================

echo "=== Preparing event simulator ==="

if [ ! -d "${REPO_DIR}/data-generators/web-events" ]; then
    echo "ERROR: Event simulator directory not found."
    exit 1
fi

rm -rf "${APP_DIR}"
mkdir -p "${APP_DIR}"

cp -a \
    "${REPO_DIR}/data-generators/web-events/." \
    "${APP_DIR}/"


# ============================================================
# 9. LIMPIAR ARCHIVOS INNECESARIOS
# ============================================================

find "${APP_DIR}" \
    -type d \
    -name "__pycache__" \
    -prune \
    -exec rm -rf {} +

find "${APP_DIR}" \
    -type f \
    \( \
        -name '._*' -o \
        -name '.DS_Store' \
    \) \
    -delete


# ============================================================
# 10. CREAR VIRTUAL ENVIRONMENT
# ============================================================

echo "=== Creating Python virtual environment ==="

python3 -m venv "${APP_DIR}/.venv"

"${APP_DIR}/.venv/bin/python" \
    -m pip install --upgrade pip


# ============================================================
# 11. INSTALAR DEPENDENCIAS DEL SIMULADOR
# ============================================================

echo "=== Installing simulator dependencies ==="

"${APP_DIR}/.venv/bin/pip" \
    install -r "${APP_DIR}/requirements.txt"


# ============================================================
# 12. CAMBIAR PROPIETARIO
# ============================================================

if id "drestrepoa2004_gmail_com" >/dev/null 2>&1; then

    chown -R \
        drestrepoa2004_gmail_com:drestrepoa2004_gmail_com \
        "${APP_DIR}"

fi


# ============================================================
# 13. LIMPIAR REPOSITORIO TEMPORAL
# ============================================================

rm -rf "${REPO_DIR}"


echo "=============================================="
echo "=== Bootstrap completed successfully ==="
echo "=============================================="
echo "PostgreSQL: installed and running"
echo "Database: ecommerce"
echo "Simulator: ${APP_DIR}"
echo "Virtual environment: ${APP_DIR}/.venv"