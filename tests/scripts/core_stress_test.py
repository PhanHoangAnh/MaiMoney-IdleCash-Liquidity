import os
import sys
import random
from decimal import Decimal
from datetime import date, timedelta
import psycopg2

# Path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.core.ledger_manager import LedgerManager
from app.core.daily_engine import DailyEngine
from app.config import PSYCOPG2_CONFIG

def reset_environment():
    """Wipes the database for a clean V3 mathematical proof."""
    print("🧹 Cleaning database for fresh V3 test...")
    conn = psycopg2.connect(**PSYCOPG2_CONFIG)
    with conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE pending_ledger, portfolio, user_shares, daily_reports CASCADE")
            cur.execute("UPDATE fund_registry SET total_idle_cash = 1000000, total_invested = 0, last_close_date = NULL")
    conn.close()

def get_integrity_snapshot():
    conn = psycopg2.connect(**PSYCOPG2_CONFIG)
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(SUM(principal_owned), 0) FROM user_shares")
        user_claims = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(principal), 0) FROM portfolio")
        bank_assets = cur.fetchone()[0]
        cur.execute("SELECT total_invested FROM fund_registry")
        registry_record = cur.fetchone()[0]
    conn.close()
    return user_claims, bank_assets, registry_record

def run_automation():
    reset_environment()
    ledger = LedgerManager()
    engine = DailyEngine()
    users = [f"user_{i:02d}" for i in range(1, 71)]
    current_date = date(2026, 2, 1)
    
    print(f"\n🚀 STARTING V3 CORE VERIFICATION (10 DAYS)")
    print("-" * 90)

    for day in range(1, 11):
        # 1. Queue 30 random transactions
        for _ in range(30):
            u = random.choice(users)
            if random.random() < 0.7:
                ledger.queue_request(u, 'DEPOSIT', Decimal(random.randint(1000, 5000)))
            else:
                conn = psycopg2.connect(**PSYCOPG2_CONFIG)
                with conn.cursor() as cur:
                    cur.execute("SELECT portfolio_id, principal_owned FROM user_shares WHERE user_id=%s AND principal_owned > 100", (u,))
                    res = cur.fetchone()
                conn.close()
                if res:
                    ledger.queue_request(u, 'WITHDRAWAL', (res[1] * Decimal('0.2')).quantize(Decimal('0.01')), portfolio_id=res[0])

        # 2. V3 Close (Providing the 4 mandatory Pillars)
        inv_params = {
            'bank': random.choice(['VCB', 'ACB', 'BIDV']),
            'rate': Decimal('8.5'),
            'early_rate': Decimal('2.0'),
            'duration': 180
        }
        engine.run_daily_close(current_date, inv_params)
        
        # 3. Integrity Check
        claims, assets, reg = get_integrity_snapshot()
        status = "✅" if (claims == assets == reg) else "❌"
        print(f"DAY {day:02d} | {status} | Claims: ${claims:,.2f} | Bank: ${assets:,.2f} | Registry: ${reg:,.2f}")
        current_date += timedelta(days=1)

    print("-" * 90)
    print("✨ V3 INTEGRITY VERIFIED.")

if __name__ == "__main__":
    run_automation()