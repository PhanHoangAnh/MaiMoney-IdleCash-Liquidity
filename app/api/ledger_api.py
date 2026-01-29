from flask import Blueprint, request, jsonify
from app.core.ledger_manager import LedgerManager
from app.core.validators import validate_user_withdrawal, simple_amount_check
from decimal import Decimal

ledger_api = Blueprint('ledger_api', __name__)
manager = LedgerManager()

@ledger_api.route('/deposit', methods=['POST'])
def deposit():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    raw_amount = data.get('amount')
    
    valid, amount = simple_amount_check(raw_amount)
    if not user_id or not valid:
        return jsonify({"error": "Missing User ID or invalid amount"}), 400
        
    try:
        manager.queue_request(user_id, 'DEPOSIT', amount)
        return jsonify({"message": f"Queued deposit for {user_id}"}), 202
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@ledger_api.route('/withdraw', methods=['POST'])
def withdraw():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    port_id = data.get('portfolio_id')
    raw_amount = data.get('amount')
    
    valid, amount = simple_amount_check(raw_amount)
    if not all([user_id, port_id is not None, valid]):
        return jsonify({"error": "Missing parameters"}), 400
        
    allowed, msg = validate_user_withdrawal(user_id, port_id, amount)
    if not allowed:
        return jsonify({"error": "Unauthorized", "reason": msg}), 403
        
    try:
        manager.queue_request(user_id, 'WITHDRAWAL', amount, portfolio_id=port_id)
        return jsonify({"message": "Withdrawal queued"}), 202
    except Exception as e:
        return jsonify({"error": str(e)}), 500