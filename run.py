from flask import Flask, render_template
import os
import sys

# Ensure the app directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.api.routes import api_blueprint
from app.api.ledger_api import ledger_api

app = Flask(__name__, 
            template_folder='app/frontend/templates', 
            static_folder='app/frontend/static')

# Register V3 Blueprints
# Dashboard API handles internal UI logic (Status, Reports, Daily Close)
app.register_blueprint(api_blueprint, url_prefix='/api/dashboard')

# Ledger API handles external CRM interactions (Deposits, Withdrawals)
app.register_blueprint(ledger_api, url_prefix='/api/ledger')

@app.route('/')
def index():
    """Serves the main Treasury Dashboard (The 'Back Office')."""
    return render_template('index.html')

@app.route('/transactions')
def transactions():
    """Serves the User Input GUI (The 'Front Office')."""
    return render_template('transactions.html')

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 LIQUIDITY LEDGER V3: SERVICE ONLINE")
    print("="*50)
    print(f"📍 Treasury Dashboard  : http://127.0.0.1:5555")
    print(f"📍 Transaction Entry  : http://127.0.0.1:5555/transactions")
    print(f"📍 External Ledger API: http://127.0.0.1:5555/api/ledger")
    print("="*50 + "\n")
    
    # Running on 0.0.0.0 to allow access within local networks/Docker
    app.run(debug=True, host='0.0.0.0', port=5555)