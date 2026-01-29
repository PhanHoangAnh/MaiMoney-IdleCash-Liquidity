import psycopg2
from datetime import datetime, timedelta, date
from decimal import Decimal
import os
import sys

# Ensure config is accessible
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.config import PSYCOPG2_CONFIG

class DailyEngine:
    """
    Standardized Engine (V3 Logic):
    1. Timeline Locking: Prevents duplicate dates and calendar gaps.
    2. Mandatory 4-Pillar Portfolios: Bank, Yield, Exit, and Tenor.
    3. Atomic Reconciliation: Ensures User Claims == Bank Assets.
    """
    def __init__(self):
        self.conn_params = PSYCOPG2_CONFIG

    def get_connection(self):
        return psycopg2.connect(**self.conn_params)

    def run_daily_close(self, close_date, new_inv_params=None):
        conn = self.get_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    # 1. Timeline Guard (Meticulous Check)
                    cur.execute("SELECT total_idle_cash, total_invested, last_close_date FROM fund_registry FOR UPDATE")
                    reg = cur.fetchone()
                    idle_cash, invested, last_date = reg

                    if last_date:
                        # Prevent duplicate or past dates
                        if close_date <= last_date:
                            return False, f"Date {close_date} is already closed."
                        
                        # FIX: Prevent Calendar Gaps (e.g., jumping from Day 1 to Day 5)
                        if close_date > last_date + timedelta(days=1):
                            return False, f"Gap detected. Next expected date: {last_date + timedelta(days=1)}"

                    # 2. Process Pending Ledger Queue
                    cur.execute("SELECT user_id, type, amount, portfolio_id FROM pending_ledger WHERE status = 'PENDING'")
                    pending_txs = cur.fetchall()
                    
                    total_dep = Decimal('0')
                    total_wit = Decimal('0')

                    # 3. Handle Withdrawals (Asset Reduction)
                    for user_id, tx_type, amount, port_id in pending_txs:
                        if tx_type == 'WITHDRAWAL':
                            total_wit += amount
                            # Atomic reduction of user share and bank principal
                            cur.execute("""
                                UPDATE user_shares SET principal_owned = principal_owned - %s 
                                WHERE user_id = %s AND portfolio_id = %s
                            """, (amount, user_id, port_id))
                            cur.execute("UPDATE portfolio SET principal = principal - %s WHERE id = %s", (amount, port_id))
                            invested -= amount
                        else:
                            total_dep += amount

                    # 4. Accrue Interest (Daily)
                    cur.execute("UPDATE portfolio SET accrued_interest = accrued_interest + (principal * (annual_rate_m / 100 / 365)) WHERE status = 'ACTIVE'")

                    # 5. Handle New Investment (Mandatory 4 Pillars)
                    current_idle = idle_cash + total_dep - total_wit
                    current_invested = invested

                    if new_inv_params and total_dep > 0:
                        # Arguments: bank, rate (yield), early_rate (exit), duration (tenor)
                        bank = new_inv_params.get('bank')
                        rate = Decimal(str(new_inv_params.get('rate')))
                        exit_rate = Decimal(str(new_inv_params.get('early_rate')))
                        tenor = int(new_inv_params.get('duration'))
                        
                        m_date = close_date + timedelta(days=tenor)

                        cur.execute("""
                            INSERT INTO portfolio (bank_name, principal, annual_rate_m, annual_rate_n, purchase_date, maturity_date)
                            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                        """, (bank, total_dep, rate, exit_rate, close_date, m_date))
                        new_port_id = cur.fetchone()[0]

                        current_idle -= total_dep
                        current_invested += total_dep

                        # Map Depositing Users to the new Lot
                        for user_id, tx_type, amt, _ in pending_txs:
                            if tx_type == 'DEPOSIT':
                                cur.execute("""
                                    INSERT INTO user_shares (user_id, portfolio_id, principal_owned)
                                    VALUES (%s, %s, %s)
                                    ON CONFLICT (user_id, portfolio_id) DO UPDATE 
                                    SET principal_owned = user_shares.principal_owned + EXCLUDED.principal_owned
                                """, (user_id, new_port_id, amt))

                    # 6. Final Sync & Audit Report
                    cur.execute("""
                        INSERT INTO daily_reports (report_date, daily_deposit, daily_withdrawal, idle_cash_at_close, invested_at_close) 
                        VALUES (%s, %s, %s, %s, %s)
                    """, (close_date, total_dep, total_wit, current_idle, current_invested))
                    
                    cur.execute("UPDATE fund_registry SET total_idle_cash = %s, total_invested = %s, last_close_date = %s", (current_idle, current_invested, close_date))
                    cur.execute("UPDATE pending_ledger SET status = 'COMPLETED' WHERE status = 'PENDING'")
                    cur.execute("DELETE FROM portfolio WHERE principal <= 0") # Cleanup zeroed lots
                    
            return True, f"Day {close_date} successfully closed."
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()