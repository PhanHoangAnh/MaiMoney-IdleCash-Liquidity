import psycopg2
from decimal import Decimal
from datetime import date
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PSYCOPG2_CONFIG

class LedgerManager:
    """
    Handles the Transaction Queue (Pending Ledger) and daily aggregation for human approval.
    """
    def __init__(self):
        self.conn_params = PSYCOPG2_CONFIG

    def queue_request(self, user_id, req_type, amount, portfolio_id=None):
        """Adds a request to the queue for later aggregation."""
        conn = psycopg2.connect(**self.conn_params)
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO pending_ledger (user_id, type, amount, portfolio_id)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, req_type.upper(), amount, portfolio_id))
        conn.close()
        return True

    def get_daily_aggregation(self):
        """Aggregates all PENDING requests for the Treasury Officer."""
        conn = psycopg2.connect(**self.conn_params)
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        SUM(CASE WHEN type = 'DEPOSIT' THEN amount ELSE 0 END) as total_dep,
                        SUM(CASE WHEN type = 'WITHDRAWAL' THEN amount ELSE 0 END) as total_wit,
                        COUNT(*) as request_count
                    FROM pending_ledger 
                    WHERE status = 'PENDING'
                """)
                res = cur.fetchone()
        conn.close()
        return {
            "total_deposit": res[0] or Decimal('0'),
            "total_withdrawal": res[1] or Decimal('0'),
            "net_flow": (res[0] or Decimal('0')) - (res[1] or Decimal('0')),
            "count": res[2]
        }

    def clear_pending_to_processed(self, cur):
        """Internal helper to mark all pending as completed during engine close."""
        cur.execute("UPDATE pending_ledger SET status = 'COMPLETED' WHERE status = 'PENDING'")