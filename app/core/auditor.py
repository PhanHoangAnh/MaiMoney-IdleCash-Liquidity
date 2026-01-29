import psycopg2
from decimal import Decimal
import os
import sys

# Ensure config is accessible
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import PSYCOPG2_CONFIG

class SystemAuditor:
    def __init__(self):
        self.conn_params = PSYCOPG2_CONFIG

    def get_full_audit_data(self):
        """Fetches raw data for both CLI and API consumption."""
        conn = psycopg2.connect(**self.conn_params)
        try:
            with conn.cursor() as cur:
                # 1. User Ownership
                cur.execute("""
                    SELECT s.user_id, p.bank_name, p.id, s.principal_owned, p.annual_rate_m
                    FROM user_shares s
                    JOIN portfolio p ON s.portfolio_id = p.id
                    ORDER BY s.user_id ASC
                """)
                users = [{"uid": r[0], "bank": r[1], "pid": r[2], "amt": r[3], "rate": r[4]} for r in cur.fetchall()]

                # 2. Portfolios (Updated to include Dates)
                cur.execute("""
                    SELECT id, bank_name, principal, accrued_interest, purchase_date, maturity_date 
                    FROM portfolio
                """)
                ports = [{
                    "id": r[0], 
                    "bank": r[1], 
                    "principal": r[2], 
                    "accrued": r[3],
                    "start": str(r[4]), 
                    "end": str(r[5])
                } for r in cur.fetchall()]

                # 3. Registry
                cur.execute("SELECT total_idle_cash, total_invested, last_close_date FROM fund_registry")
                reg_raw = cur.fetchone()
                registry = {
                    "idle": reg_raw[0],
                    "invested": reg_raw[1],
                    "last_close": str(reg_raw[2])
                }

                return {"users": users, "portfolios": ports, "registry": registry}
        finally:
            conn.close()