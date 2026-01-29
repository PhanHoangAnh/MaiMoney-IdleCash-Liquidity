import sys
import os
from decimal import Decimal
from datetime import date

# Ensure the root directory is in the path for modular imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.ledger_manager import LedgerManager
from app.core.daily_engine import DailyEngine
from app.core.validators import validate_user_withdrawal, simple_amount_check
from app.core.auditor import SystemAuditor
from tabulate import tabulate

def main():
    ledger = LedgerManager()
    engine = DailyEngine()

    print("\n" + "="*60)
    print("🏦 LIQUIDITY LEDGER V3: TERMINAL COMMAND CENTER")
    print("="*60)
    
    while True:
        print("\n[1] Queue Deposit")
        print("[2] Queue Withdrawal")
        print("[3] Review & Close Day (V3 Protocol)")
        print("[4] Run Full Audit")
        print("[Q] Quit")
        
        choice = input("\nSelect Action: ").strip().upper()

        if choice == '1':
            uid = input("  Customer ID: ").strip()
            raw_amt = input("  Deposit Amount ($): ")
            
            valid, amt = simple_amount_check(raw_amt)
            if valid:
                ledger.queue_request(uid, 'DEPOSIT', amt)
                print(f"✅ Queued: ${amt:,.2f} for {uid}")
            else:
                print("❌ Error: Invalid amount.")

        elif choice == '2':
            uid = input("  Customer ID: ").strip()
            try:
                pid = int(input("  From Portfolio ID: "))
                raw_amt = input("  Withdrawal Amount ($): ")
                
                valid, amt = simple_amount_check(raw_amt)
                if not valid:
                    print("❌ Error: Invalid amount.")
                    continue

                # V3 Security Validation
                allowed, msg = validate_user_withdrawal(uid, pid, amt)
                if allowed:
                    ledger.queue_request(uid, 'WITHDRAWAL', amt, portfolio_id=pid)
                    print(f"✅ Queued: Withdrawal of ${amt:,.2f}")
                else:
                    print(f"⚠️ Rejected: {msg}")
            except ValueError:
                print("❌ Error: Portfolio ID must be an integer.")

        elif choice == '3':
            summary = ledger.get_daily_aggregation()
            print(f"\n" + "-"*40)
            print(f"📊 PENDING SUMMARY")
            print(f"Total Deposits  : ${summary['total_deposit']:,.2f}")
            print(f"Total Withdraws : ${summary['total_withdrawal']:,.2f}")
            print(f"Net Position    : ${summary['net_flow']:,.2f}")
            print("-"*40)
            
            if summary['count'] == 0:
                print("ℹ️ No pending transactions found.")
                continue

            confirm = input("\nApprove Daily Close? (y/n): ").lower()
            if confirm == 'y':
                inv_params = None
                # If there's money to invest, V3 requires the 4 Pillars
                if summary['net_flow'] > 0:
                    print("\n📜 V3 MANDATORY INVESTMENT PARAMS")
                    bank = input("  1. Bank Name (e.g. VCB): ")
                    yield_r = input("  2. Yield Rate (%): ")
                    exit_r = input("  3. Exit/Early Rate (%): ")
                    tenor = input("  4. Tenor (Days): ")
                    
                    try:
                        inv_params = {
                            'bank': bank,
                            'rate': Decimal(yield_r),
                            'early_rate': Decimal(exit_r),
                            'duration': int(tenor)
                        }
                    except:
                        print("❌ Error: Invalid investment parameters. Close aborted.")
                        continue
                
                # Execute engine with Timeline Lock
                success, msg = engine.run_daily_close(date.today(), inv_params)
                if success:
                    print(f"\n✨ SUCCESS: {msg}")
                else:
                    print(f"\n🔥 ENGINE ERROR: {msg}")

        elif choice == 'Q':
            print("👋 Session Closed.")
            break
        
        elif choice == '4':
            auditor = SystemAuditor()
            data = auditor.get_full_audit_data()

            print("\n" + "="*80)
            print("🔍 FULL SYSTEM INTEGRITY AUDIT")
            print("="*80)

            # User Ownership
            print("\n[A] USER OWNERSHIP BREAKDOWN")
            headers_a = ["User ID", "Bank", "Portfolio ID", "Principal Owned", "Rate (%)"]
            table_a = [[r["uid"], r["bank"], r["pid"], float(r["amt"]), float(r["rate"])] for r in data["users"]]
            print(tabulate(table_a, headers=headers_a, tablefmt="grid"))

            # Updated Portfolio Totals Table
            print("\n[B] PORTFOLIO SUMMARY & TIMELINE")
            headers_b = ["ID", "Bank", "Principal", "Accrued", "Start Date", "Maturity"]
            table_b = [
                [r["id"], r["bank"], float(r["principal"]), float(r["accrued"]), r["start"], r["end"]] 
                for r in data["portfolios"]
            ]
            print(tabulate(table_b, headers=headers_b, tablefmt="grid"))

            # Registry Totals
            reg = data["registry"]
            print("\n[C] REGISTRY SUMMARY")
            print(f"Total Idle Cash: ${float(reg['idle']):,.2f}")
            print(f"Total Invested: ${float(reg['invested']):,.2f}")
            print(f"Last Close Date: {reg['last_close']}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Forced Exit.")
        sys.exit(0)