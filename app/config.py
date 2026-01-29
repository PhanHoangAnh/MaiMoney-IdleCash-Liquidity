import os

# --- DATABASE CONFIGURATION V2 ---
# Using a unique name to isolate from previous PoC
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "convit")
DB_NAME = os.getenv("DB_NAME", "ledger_liquidity_v2") # New Isolated DB

# Connection strings
SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"

PSYCOPG2_CONFIG = {
    "host": DB_HOST,
    "user": DB_USER,
    "password": DB_PASS,
    "database": DB_NAME
}

# Maintenance config used to create/drop the main DB
MAINTENANCE_CONFIG = {
    "host": DB_HOST,
    "user": DB_USER,
    "password": DB_PASS,
    "database": "postgres"
}