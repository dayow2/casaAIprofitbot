import os
import threading
import time
import logging
import asyncio
from flask import Flask, render_template_string, jsonify
from metaapi_cloud_sdk import MetaApi

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Flask App Setup ---
app = Flask(__name__)

# --- Global Bot State & Config ---
bot_running = False
trading_thread = None
current_order_id = None
ENTRY_PRICE = 10.00
TAKE_PROFIT_PRICE = 10.50
SYMBOL = 'EURUSD'  # Or your preferred forex pair

# --- MetaApi Client Setup ---
API_TOKEN = os.getenv('API_KEY')
ACCOUNT_ID = os.getenv('ACCOUNT_ID')

# Initialize MetaApi client (it just holds the token)
api = MetaApi(token=API_TOKEN)
mt_account = None
connection = None

async def initialize_metaapi():
    """Initialize MetaApi account and connection."""
    global mt_account, connection
    try:
        mt_account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        connection = mt_account.get_streaming_connection()
        await connection.connect()
        logger.info("Connected to MetaApi successfully.")
        await connection.wait_synchronized()
        logger.info("MetaApi account synchronized.")
        return True
    except Exception as e:
        logger.error(f"Error initializing MetaApi: {e}")
        return False

def run_async(coro):
    """Helper to run async code from sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

def get_current_price():
    """Get real-time price via MetaApi."""
    if not connection:
        return None
    try:
        price = run_async(connection.get_symbol_price(SYMBOL))
        return price['bid']
    except Exception as e:
        logger.error(f"Error getting price: {e}")
        return None

def place_buy_order():
    """Place a buy market order."""
    global current_order_id
    try:
        trade = run_async(connection.create_market_buy_order(SYMBOL, 0.01, TAKE_PROFIT_PRICE, None))
        current_order_id = trade['id']
        logger.info(f"Placed market BUY order {current_order_id}")
        return current_order_id
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        return None

def close_all_orders():
    """Close all open positions."""
    global current_order_id
    try:
        if current_order_id:
            run_async(connection.close_order(current_order_id))
            logger.info("Closed all positions.")
            current_order_id = None
    except Exception as e:
        logger.error(f"Error closing order: {e}")

def trading_loop():
    """Arbitrage monitoring loop."""
    global bot_running, current_order_id
    logger.info("Arbitrage bot started.")
    while bot_running:
        if not connection:
            time.sleep(5)
            continue
        price = get_current_price()
        if price is None:
            time.sleep(5)
            continue
        logger.info(f"Current price: {price}")
        if not current_order_id and price <= ENTRY_PRICE:
            place_buy_order()
        elif current_order_id and price >= TAKE_PROFIT_PRICE:
            close_all_orders()
        time.sleep(1)
    logger.info("Arbitrage bot stopped.")

# --- Flask Routes (The 4 Buttons) ---

@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE)

@app.route('/start')
def start_trading():
    global bot_running, trading_thread
    if not bot_running:
        # Re-initialize connection if needed
        if not connection:
            if not run_async(initialize_metaapi()):
                return jsonify({'status': 'error', 'message': 'Failed to connect to MetaApi'}), 500
        bot_running = True
        trading_thread = threading.Thread(target=trading_loop, daemon=True)
        trading_thread.start()
        logger.info("Start command received.")
        return jsonify({'status': 'started'})
    return jsonify({'status': 'already_running'})

@app.route('/stop')
def stop_trading():
    global bot_running
    if bot_running:
        bot_running = False
        logger.info("Stop command received.")
        return jsonify({'status': 'stopped'})
    return jsonify({'status': 'already_stopped'})

@app.route('/orders')
def show_orders():
    if current_order_id:
        return jsonify({'status': 'success', 'order_id': current_order_id})
    return jsonify({'status': 'success', 'order_id': None})

@app.route('/take_profit')
def take_profit():
    close_all_orders()
    return jsonify({'status': 'profit_taken'})

# --- HTML Template (The 4-Button Dashboard) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MT4 Arbitrage Bot Dashboard</title>
    <style>
        body { font-family: monospace; text-align: center; margin-top: 50px; background: #1e1e2f; color: white; }
        .btn { padding: 15px 32px; margin: 10px; font-size: 16px; cursor: pointer; border: none; border-radius: 8px; transition: 0.2s; }
        .btn-start { background-color: #4CAF50; color: white; }
        .btn-stop { background-color: #f44336; color: white; }
        .btn-orders { background-color: #008CBA; color: white; }
        .btn-profit { background-color: #ff9800; color: white; }
        .btn:hover { transform: scale(1.05); opacity: 0.9; }
        .status { margin-top: 30px; padding: 15px; background: #2d2d44; border-radius: 10px; display: inline-block; }
        #orderDisplay { font-weight: bold; color: #ffaa00; }
    </style>
</head>
<body>
    <h1>🤖 MT4 Arbitrage Bot</h1>
    <div>
        <button class="btn btn-start" onclick="callApi('/start')">▶️ 1. Start Trading</button>
        <button class="btn btn-orders" onclick="callApi('/orders')">📋 2. Show Current Orders</button>
        <button class="btn btn-profit" onclick="callApi('/take_profit')">💰 3. Take Profit</button>
        <button class="btn btn-stop" onclick="callApi('/stop')">⏹️ 4. Stop Trading</button>
    </div>
    <div class="status">
        <p>📊 Bot Status: <span id="statusMsg">Stopped</span></p>
        <p>📈 Current Order: <span id="orderDisplay">None</span></p>
    </div>
    <script>
        async function callApi(endpoint) {
            const response = await fetch(endpoint);
            const data = await response.json();
            if (endpoint === '/orders' && data.order_id) {
                document.getElementById('orderDisplay').innerText = data.order_id;
            } else if (endpoint === '/orders' && !data.order_id) {
                document.getElementById('orderDisplay').innerText = 'None';
            } else if (data.status === 'started') {
                document.getElementById('statusMsg').innerText = 'Running';
            } else if (data.status === 'stopped') {
                document.getElementById('statusMsg').innerText = 'Stopped';
                document.getElementById('orderDisplay').innerText = 'None';
            }
        }
        setInterval(() => callApi('/orders'), 5000);
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
