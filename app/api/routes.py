from flask import Blueprint, jsonify, request
import psycopg2
from app.config import PSYCOPG2_CONFIG
from app.core.ledger_manager import LedgerManager
from app.core.daily_engine import DailyEngine
from app.core.auditor import SystemAuditor
from datetime import datetime, timedelta

api_blueprint = Blueprint('dashboard_api', __name__)
ledger = LedgerManager()
engine = DailyEngine()
auditor = SystemAuditor()

@api_blueprint.route('/status', methods=['GET'])
def get_status():
    """Summarizes system health with performance metrics."""
    conn = psycopg2.connect(**PSYCOPG2_CONFIG)
    with conn.cursor() as cur:
        cur.execute("SELECT total_idle_cash, total_invested, last_close_date FROM fund_registry")
        reg = cur.fetchone()
        idle, inv, last_date = reg if reg else (0, 0, None)
        
        cur.execute("SELECT COALESCE(SUM(principal_owned), 0) FROM user_shares")
        liability = cur.fetchone()[0]
        
        cur.execute("SELECT COALESCE(SUM(accrued_interest), 0) FROM portfolio")
        shadow_profit = cur.fetchone()[0]
        
        realized_pnl = 0.00 
        next_date = last_date + timedelta(days=1) if last_date else datetime.now().date()
        
    conn.close()
    return jsonify({
        "idle_cash": float(idle),
        "total_invested": float(inv),
        "total_liability": float(liability),
        "shadow_profit": float(shadow_profit),
        "realized_pnl": float(realized_pnl),
        "last_close_date": str(last_date) if last_date else None,
        "next_expected_date": str(next_date)
    })

@api_blueprint.route('/pending-summary', methods=['GET'])
def get_pending_summary():
    """Aggregated stats for the header."""
    return jsonify(ledger.get_daily_aggregation())

@api_blueprint.route('/pending-list', methods=['GET'])
def get_pending_list():
    """Granular list of transactions for editing/deleting in FrontOffice."""
    return jsonify(ledger.get_pending_list())

@api_blueprint.route('/pending/<int:tx_id>', methods=['DELETE'])
def cancel_pending(tx_id):
    """Cancels a pending request."""
    try:
        ledger.cancel_pending(tx_id)
        return jsonify({"message": "Transaction canceled"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_blueprint.route('/pending/<int:tx_id>', methods=['PATCH'])
def update_pending(tx_id):
    """Updates a pending request amount."""
    data = request.get_json()
    new_amount = data.get('amount')
    try:
        ledger.update_pending(tx_id, new_amount)
        return jsonify({"message": "Transaction updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_blueprint.route('/audit/full', methods=['GET'])
def get_audit():
    return jsonify(auditor.get_full_audit_data())

@api_blueprint.route('/reports', methods=['GET'])
def get_reports():
    conn = psycopg2.connect(**PSYCOPG2_CONFIG)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT report_date, daily_deposit, daily_withdrawal, idle_cash_at_close, invested_at_close 
            FROM daily_reports ORDER BY report_date DESC LIMIT 15
        """)
        rows = cur.fetchall()
    conn.close()
    return jsonify([{
        "date": str(r[0]), "in": float(r[1]), "out": float(r[2]), 
        "idle": float(r[3]), "invested": float(r[4])
    } for r in rows])

@api_blueprint.route('/history/<target_date>', methods=['GET'])
def get_history(target_date):
    conn = psycopg2.connect(**PSYCOPG2_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT user_id, type, amount FROM pending_ledger 
                WHERE status = 'COMPLETED' AND created_at::date = %s
            """, (target_date,))
            rows = cur.fetchall()
            return jsonify([{"user_id": r[0], "type": r[1], "amount": float(r[2])} for r in rows])
    finally:
        conn.close()

@api_blueprint.route('/close-day', methods=['POST'])
def close_day():
    data = request.get_json() or {}
    target_date_str = data.get('date')
    inv_params = data.get('investment_params')
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        success, msg = engine.run_daily_close(target_date, inv_params)
        return jsonify({"message": msg}) if success else (jsonify({"error": msg}), 400)
    except Exception as e:
        return jsonify({"error": str(e)}), 500