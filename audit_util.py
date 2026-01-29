import psycopg2
from decimal import Decimal
from tabulate import tabulate # You may need to: pip install tabulate
import os
import sys

# Ensure config is accessible
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.config import PSYCOPG2_CONFIG

def fetch_audit_data():
    conn = psycopg2.connect(**PSYCOPG2_CONFIG)
    try:
        with conn.cursor() as cur:
            # 1. Detailed User-Portfolio Breakdown
            cur.execute("""
                SELECT 
                    s.user_id, 
                    p.bank_name, 
                    p.id as port_id,
                    s.principal_owned,
                    p.annual_rate_m
                FROM user_shares s
                JOIN portfolio p ON s.portfolio_id = p.id
                ORDER BY s.user_id ASC, p.id ASC
            """)
            user_details = cur.fetchall()

            # 2. Portfolio Totals (Bank View)
            cur.execute("SELECT id, bank_name, principal, accrued_interest FROM portfolio")
            port_summaries = cur.fetchall()

            # 3. Registry Totals (The Source of Truth)
            cur.execute("SELECT total_idle_cash, total_invested, last_close_date FROM fund_registry")
            registry = cur.fetchone()

        return user_details, port_summaries, registry
    finally:
        conn.close()

def run_audit_report():
    user_details, port_summaries, reg = fetch_audit_data()
    
    print("\n" + "="*80)
    print(f"🔍 LIQUIDITY V3 SYSTEM AUDIT | Last Close: {reg[2]}")
    print("="*80)

    # Section A: User Ownership List
    print("\n[A] INDIVIDUAL USER OWNERSHIP (PRO-RATA SHARES)")
    headers_a = ["User ID", "Bank", "Port ID", "Principal Owned", "Rate (%)"]
    # Formatting for currency
    formatted_users = [[u[0], u[1], u[2], f"${u[3]:,.2f}", f"{u[4]}%"] for u in user_details]
    print(tabulate(formatted_users, headers=headers_a, tablefmt="presto"))

    # Section B: Portfolio/Bank Lots
    print("\n[B] ACTIVE BANK PORTFOLIOS")
    headers_b = ["ID", "Bank Name", "Total Principal", "Accrued (Unallocated)"]
    formatted_ports = [[p[0], p[1], f"${p[2]:,.2f}", f"${p[3]:,.8f}"] for p in port_summaries]
    print(tabulate(formatted_ports, headers=headers_b, tablefmt="presto"))

    # Section C: System Reconciliation
    total_claims = sum(u[3] for u in user_details)
    total_bank_assets = sum(p[2] for p in port_summaries)
    
    print("\n[C] ATOMIC RECONCILIATION")
    print(f"  Total User Claims  : ${total_claims:,.2f}")
    print(f"  Total Bank Assets  : ${total_bank_assets:,.2f}")
    print(f"  Registry Invested  : ${reg[1]:,.2f}")
    print(f"  Registry Idle Cash : ${reg[0]:,.2f}")
    
    diff = total_claims - total_bank_assets
    status = "✅ CLEAN" if diff == 0 else f"❌ DISCREPANCY: ${diff:,.2f}"
    print(f"  Integrity Status   : {status}")
    print("="*80 + "\n")

if __name__ == "__main__":
    run_audit_report()