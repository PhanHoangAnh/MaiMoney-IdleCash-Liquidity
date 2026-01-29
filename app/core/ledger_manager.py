import psycopg2
from decimal import Decimal
from datetime import date
import os
import sys

# Ensure config is accessible
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import PSYCOPG2_CONFIG

class LedgerManager:
    """
    Handles the Transaction Queue (Pending Ledger) and daily aggregation.
    Updated V3.1: Includes granular management for editing/canceling pending entries.
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

    def get_pending_list(self):
        """Fetches individual pending transactions for the FrontOffice UI."""
        conn = psycopg2.connect(**self.conn_params)
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, user_id, type, amount, portfolio_id, created_at 
                    FROM pending_ledger 
                    WHERE status = 'PENDING' 
                    ORDER BY created_at DESC
                """)
                rows = cur.fetchall()
        conn.close()
        return [{
            "id": r[0], 
            "user_id": r[1], 
            "type": r[2], 
            "amount": float(r[3]), 
            "portfolio_id": r[4], 
            "created_at": r[5].strftime("%H:%M:%S")
        } for r in rows]

    def cancel_pending(self, tx_id):
        """Removes a specific transaction from the pending queue."""
        conn = psycopg2.connect(**self.conn_params)
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM pending_ledger WHERE id = %s AND status = 'PENDING'", (tx_id,))
        conn.close()
        return True

    def update_pending(self, tx_id, new_amount):
        """Updates the amount for an existing pending entry."""
        conn = psycopg2.connect(**self.conn_params)
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE pending_ledger 
                    SET amount = %s 
                    WHERE id = %s AND status = 'PENDING'
                """, (new_amount, tx_id))
        conn.close()
        return True

    def get_daily_aggregation(self):
        """Aggregates all PENDING requests for the Treasury summary."""
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