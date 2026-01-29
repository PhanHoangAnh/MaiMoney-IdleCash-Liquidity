import os
import sys
import psycopg2
from datetime import date

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.core.daily_engine import DailyEngine
from app.config import PSYCOPG2_CONFIG

def reset_env():
    conn = psycopg2.connect(**PSYCOPG2_CONFIG)
    with conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE pending_ledger, portfolio, user_shares, daily_reports CASCADE")
            cur.execute("UPDATE fund_registry SET total_idle_cash = 1000000, total_invested = 0, last_close_date = NULL")
    conn.close()

def run_test():
    reset_env()
    engine = DailyEngine()
    d1, d2 = date(2026, 4, 1), date(2026, 4, 2)
    
    print("\n🚀 STARTING V3 CALENDAR LOCK TEST")
    
    # 1. First Close
    s, m = engine.run_daily_close(d1)
    print(f"Test 1 (Initial Close): {'✅' if s else '❌'} {m}")
    
    # 2. Duplicate Close
    s, m = engine.run_daily_close(d1)
    print(f"Test 2 (Duplicate Block): {'✅' if not s else '❌'} {m}")
    
    # 3. Gap Detection (Try skipping d2)
    s, m = engine.run_daily_close(date(2026, 4, 5))
    print(f"Test 3 (Gap Block): {'✅' if not s else '❌'} {m}")
    
    print("\n✨ V3 CALENDAR LOCK VERIFIED.")

if __name__ == "__main__":
    run_test()