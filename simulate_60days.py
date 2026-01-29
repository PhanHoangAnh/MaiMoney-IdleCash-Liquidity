import os
import sys
import random
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
import psycopg2

# Path setup to ensure internal modules are importable
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.ledger_manager import LedgerManager
from app.core.daily_engine import DailyEngine
from app.core.auditor import SystemAuditor
from app.config import PSYCOPG2_CONFIG

def reset_environment():
    """Wipes the database and resets the registry to Day Zero."""
    print("🧹 Wiping database for fresh 60-day simulation...")
    conn = psycopg2.connect(**PSYCOPG2_CONFIG)
    with conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE pending_ledger, portfolio, user_shares, daily_reports CASCADE")
            cur.execute("UPDATE fund_registry SET total_idle_cash = 1000000, total_invested = 0, last_close_date = NULL")
    conn.close()

def get_users_with_balances():
    """Queries current holders to allow for realistic withdrawals."""
    conn = psycopg2.connect(**PSYCOPG2_CONFIG)
    with conn.cursor() as cur:
        cur.execute("SELECT user_id, portfolio_id, principal_owned FROM user_shares WHERE principal_owned > 10")
        results = cur.fetchall()
    conn.close()
    return results

def run_simulation():
    # 1. Initialize Core Engines
    reset_environment()
    ledger = LedgerManager()
    engine = DailyEngine()
    auditor = SystemAuditor()
    
    # 2. Setup Parameters
    user_pool = [f"Client_{i:03d}" for i in range(1, 101)]
    banks = ["VCB", "ACB", "BIDV", "Techcombank", "TPBank"]
    start_date = date(2026, 1, 1)
    
    print(f"\n🚀 STARTING 60-DAY LIQUIDITY SIMULATION")
    print("=" * 100)
    print(f"{'DAY':<5} | {'DATE':<12} | {'DEPOSITS':<10} | {'WITHDRAWS':<10} | {'NET FLOW':<12} | {'STATUS'}")
    print("-" * 100)

    for d in range(60):
        current_date = start_date + timedelta(days=d)
        
        # --- PHASE A: RANDOM TRANSACTIONS ---
        num_txs = random.randint(20, 50)
        daily_users_with_balance = get_users_with_balances()

        for _ in range(num_txs):
            # 70% chance of deposit, 30% chance of withdrawal
            if random.random() < 0.7 or not daily_users_with_balance:
                # Deposit
                u = random.choice(user_pool)
                amt = Decimal(random.uniform(500, 15000)).quantize(Decimal('0.01'))
                ledger.queue_request(u, 'DEPOSIT', amt)
            else:
                # Withdrawal (Pick from actual holders)
                holder = random.choice(daily_users_with_balance)
                u_id, p_id, balance = holder
                # Withdraw between 5% and 50% of their holding
                amt = (balance * Decimal(random.uniform(0.05, 0.5))).quantize(Decimal('0.01'))
                if amt > 0:
                    ledger.queue_request(u_id, 'WITHDRAWAL', amt, portfolio_id=p_id)

        # --- PHASE B: DAILY CLOSE ---
        summary = ledger.get_daily_aggregation()
        
        # Prepare V3 Pillars for new deployment
        inv_params = None
        if summary['net_flow'] > 0:
            inv_params = {
                'bank': random.choice(banks),
                'rate': Decimal(random.uniform(7.0, 9.5)).quantize(Decimal('0.1')),
                'early_rate': Decimal('2.0'),
                'duration': random.choice([180, 360])
            }

        success, msg = engine.run_daily_close(current_date, inv_params)
        
        # --- PHASE C: INTEGRITY AUDIT ---
        audit = auditor.get_full_audit_data()
        
        # Math Proof: Sum(User Shares) must equal Sum(Portfolio Principals)
        total_user_claims = sum(Decimal(str(u['amt'])) for u in audit['users'])
        total_bank_assets = sum(Decimal(str(p['principal'])) for p in audit['portfolios'])
        
        diff = (total_user_claims - total_bank_assets).copy_abs()
        integrity = "✅ OK" if diff < Decimal('0.01') else f"❌ FAIL (${diff})"
        
        # Log Progress
        print(f"{d+1:<5} | {str(current_date):<12} | ${summary['total_deposit']:>9,.2f} | ${summary['total_withdrawal']:>9,.2f} | ${summary['net_flow']:>11,.2f} | {integrity}")

    # Final Summary
    final_audit = auditor.get_full_audit_data()
    reg = final_audit['registry']
    print("-" * 100)
    print(f"🏁 SIMULATION COMPLETE")
    print(f"   Final Total Invested : ${float(reg['invested']):,.2f}")
    print(f"   Final Idle Cash      : ${float(reg['idle']):,.2f}")
    print(f"   Final Active Lots    : {len(final_audit['portfolios'])}")
    print(f"   Active User Accounts : {len(set(u['uid'] for u in final_audit['users']))}")
    print("=" * 100 + "\n")

if __name__ == "__main__":
    try:
        run_simulation()
    except KeyboardInterrupt:
        print("\nSimulation aborted.")
    except Exception as e:
        print(f"\nSimulation crashed: {e}")