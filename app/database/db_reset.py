import psycopg2
import os
import sys

# Ensure config is accessible
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.config import PSYCOPG2_CONFIG

def reset_database():
    """
    Wipes all transaction, portfolio, and report data.
    Resets the Fund Registry to the initial starting state.
    """
    print(f"🧨 WARNING: Resetting database '{PSYCOPG2_CONFIG['database']}'...")
    
    try:
        conn = psycopg2.connect(**PSYCOPG2_CONFIG)
        with conn:
            with conn.cursor() as cur:
                # 1. Truncate all transactional and relational data
                # CASCADE ensures that dependent records are also removed
                print("🧹 Truncating tables...")
                cur.execute("""
                    TRUNCATE 
                        pending_ledger, 
                        portfolio, 
                        user_shares, 
                        daily_reports, 
                        transaction_history 
                    RESTART IDENTITY CASCADE;
                """)

                # 2. Reset the Fund Registry to initial state
                # 1,000,000 Idle Cash, 0 Invested, No previous close date
                print("🔄 Resetting Fund Registry...")
                cur.execute("""
                    UPDATE fund_registry 
                    SET 
                        total_idle_cash = 1000000.00, 
                        total_invested = 0.00, 
                        last_close_date = NULL;
                """)
                
        conn.close()
        print("✨ Database reset successfully. System is now back to Day Zero.")
        
    except Exception as e:
        print(f"❌ Error during reset: {e}")

if __name__ == "__main__":
    confirm = input("Are you sure you want to wipe ALL data? (y/n): ").lower()
    if confirm == 'y':
        reset_database()
    else:
        print("Reset aborted.")