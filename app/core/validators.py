import psycopg2
from decimal import Decimal
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import PSYCOPG2_CONFIG

def validate_user_withdrawal(user_id, portfolio_id, amount_to_withdraw):
    """
    Standardized Validator (V3 Logic):
    Verifies user has sufficient principal in the specified lot.
    """
    conn = psycopg2.connect(**PSYCOPG2_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT principal_owned FROM user_shares 
                WHERE user_id = %s AND portfolio_id = %s
            """, (user_id, portfolio_id))
            row = cur.fetchone()
            
            if not row:
                return False, "Security Error: No ownership record found."
            
            owned = row[0]
            if Decimal(str(amount_to_withdraw)) > owned:
                return False, f"Insufficient balance. Available: ${owned:,.2f}"
            
            return True, "Valid"
    finally:
        conn.close()

def simple_amount_check(amount):
    """Numeric check for currency inputs."""
    try:
        val = Decimal(str(amount))
        return val > 0, val
    except:
        return False, Decimal('0')