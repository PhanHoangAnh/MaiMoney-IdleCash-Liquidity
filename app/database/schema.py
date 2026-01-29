import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import sys

# Ensure config is accessible
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MAINTENANCE_CONFIG, PSYCOPG2_CONFIG

def initialize_v3_db():
    """
    Initializes the V3 Schema. Focuses on the 4 pillars of portfolio creation:
    Bank Name, Yield (rate_m), Exit (rate_n), and Tenor (duration).
    """
    new_db = PSYCOPG2_CONFIG['database']
    
    # 1. DB Creation
    conn_m = psycopg2.connect(**MAINTENANCE_CONFIG)
    conn_m.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur_m = conn_m.cursor()
    cur_m.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (new_db,))
    if not cur_m.fetchone():
        cur_m.execute(f'CREATE DATABASE {new_db}')
    cur_m.close()
    conn_m.close()

    # 2. Table Creation
    conn = psycopg2.connect(**PSYCOPG2_CONFIG)
    cur = conn.cursor()

    # PORTFOLIO: Optimized for the 4 mandatory arguments
    cur.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id SERIAL PRIMARY KEY,
            bank_name VARCHAR(255) NOT NULL,    -- Argument 1: Bank Name
            principal DECIMAL(20, 2) NOT NULL,
            accrued_interest DECIMAL(20, 2) DEFAULT 0,
            annual_rate_m DECIMAL(10, 5) NOT NULL, -- Argument 2: Yield (Rate)
            annual_rate_n DECIMAL(10, 5) NOT NULL, -- Argument 3: Exit (Early)
            purchase_date DATE NOT NULL,
            maturity_date DATE NOT NULL,           -- Derived from Argument 4: Tenor
            status VARCHAR(20) DEFAULT 'ACTIVE'
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pending_ledger (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(100) NOT NULL,
            type VARCHAR(20),
            amount DECIMAL(20, 2) NOT NULL,
            portfolio_id INTEGER,
            status VARCHAR(20) DEFAULT 'PENDING',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_shares (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(100) NOT NULL,
            portfolio_id INTEGER REFERENCES portfolio(id),
            principal_owned DECIMAL(20, 2) NOT NULL,
            UNIQUE(user_id, portfolio_id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS fund_registry (
            id SERIAL PRIMARY KEY,
            total_idle_cash DECIMAL(20, 2) DEFAULT 0,
            total_invested DECIMAL(20, 2) DEFAULT 0,
            last_close_date DATE
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_reports (
            id SERIAL PRIMARY KEY,
            report_date DATE UNIQUE NOT NULL,
            daily_deposit DECIMAL(20, 2),
            daily_withdrawal DECIMAL(20, 2),
            idle_cash_at_close DECIMAL(20, 2),
            invested_at_close DECIMAL(20, 2)
        );
    """)

    cur.execute("SELECT COUNT(*) FROM fund_registry")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO fund_registry (total_idle_cash) VALUES (1000000.00)")

    conn.commit()
    cur.close()
    conn.close()
    print(f"✨ V3 Schema Initialized for {new_db}")

if __name__ == "__main__":
    initialize_v3_db()