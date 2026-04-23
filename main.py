import os
import threading
import time
import random
import logging
from flask import Flask, render_template_string, jsonify

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- Bot State ---
bot_running = False
trading_thread = None
current_order = None
current_price = 10.00  # Starting price
entry_price = 10.00
take_profit_price = 10.50

# --- Simulated Price Movement ---
def simulate_price():
    """Generate realistic price movement +/- 0.05"""
    global current_price
    change = random.uniform(-0.03, 0.03)
    current_price = round(current_price + change, 2)
    # Keep price between $9 and $11
    if current_price < 9:
        current_price = 9
    if current_price > 11:
        current_price = 11
    return current_price

# --- Trading Logic ---
def place_order():
    global current_order
    current_order = {
        'id': random.randint(10000, 99999),
        'entry_price': current_price,
        'take_profit': take_profit_price,
        'status': 'OPEN'
    }
    logger.info(f"✅ BUY ORDER PLACED at ${current_price}")
    return current_order

def close_order():
    global current_order
    if current_order:
        profit = round(take_profit_price - current_order['entry_price'], 2)
        logger.info(f"💰 ORDER CLOSED - Profit: ${profit}")
        current_order = None

def trading_loop():
    """Main trading logic"""
    global bot_running, current_order
    logger.info("🤖 Bot Started - Monitoring prices...")
    
    while bot_running:
        price = simulate_price()
        logger.info(f"Current Price: ${price}")
        
        # Entry condition: Price drops to $10 or below, and no open order
        if not current_order and price <= entry_price:
            place_order()
        
        # Exit condition: Price reaches $10.50 or above, and order exists
        elif current_order and price >= take_profit_price:
            close_order()
        
        time.sleep(2)  # Check every 2 seconds
    
    logger.info("🛑 Bot Stopped")

# --- Web Routes (4 Buttons) ---
@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE)

@app.route('/start')
def start_trading():
    global bot_running, trading_thread
    if not bot_running:
        bot_running = True
        trading_thread = threading.Thread(target=trading_loop, daemon=True)
        trading_thread.start()
        return jsonify({'status': 'started', 'price': current_price})
    return jsonify({'status': 'already_running'})

@app.route('/stop')
def stop_trading():
    global bot_running
    bot_running = False
    return jsonify({'status': 'stopped'})

@app.route('/orders')
def show_orders():
    if current_order:
        return jsonify({
            'status': 'success',
            'order_id': current_order['id'],
            'entry_price': current_order['entry_price'],
            'take_profit': current_order['take_profit']
        })
    return jsonify({'status': 'success', 'order_id': None})

@app.route('/take_profit')
def take_profit():
    close_order()
    return jsonify({'status': 'profit_taken'})

@app.route('/price')
def get_price():
    return jsonify({'price': current_price})

# --- HTML Dashboard ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Forex Arbitrage Bot Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }
        .price-display {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 30px;
        }
        .price-label {
            font-size: 18px;
            opacity: 0.9;
        }
        .price-value {
            font-size: 48px;
            font-weight: bold;
            margin: 10px 0;
        }
        .price-change {
            font-size: 14px;
        }
        .button-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }
        .btn {
            padding: 15px;
            font-size: 16px;
            font-weight: bold;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .btn-start { background: #10b981; color: white; }
        .btn-orders { background: #3b82f6; color: white; }
        .btn-profit { background: #f59e0b; color: white; }
        .btn-stop { background: #ef4444; color: white; }
        .status-card {
            background: #f3f4f6;
            border-radius: 10px;
            padding: 15px;
            margin-top: 20px;
        }
        .status-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e5e7eb;
        }
        .status-item:last-child { border-bottom: none; }
        .status-label { font-weight: bold; color: #4b5563; }
        .status-value { color: #1f2937; font-family: monospace; }
        .profit { color: #10b981; font-weight: bold; }
        .loss { color: #ef4444; font-weight: bold; }
        .alert {
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 10px;
            margin-top: 15px;
            border-radius: 5px;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Forex Arbitrage Bot</h1>
        <div class="subtitle">Simple Buy Low, Sell High Strategy</div>
        
        <div class="price-display">
            <div class="price-label">Current Market Price</div>
            <div class="price-value" id="price">$10.00</div>
            <div class="price-change" id="change">Waiting for updates...</div>
        </div>
        
        <div class="button-grid">
            <button class="btn btn-start" onclick="callApi('/start')">▶️ Start Trading</button>
            <button class="btn btn-orders" onclick="callApi('/orders')">📋 Show Orders</button>
            <button class="btn btn-profit" onclick="callApi('/take_profit')">💰 Take Profit</button>
            <button class="btn btn-stop" onclick="callApi('/stop')">⏹️ Stop Trading</button>
        </div>
        
        <div class="status-card">
            <div class="status-item">
                <span class="status-label">Bot Status:</span>
                <span class="status-value" id="botStatus">Stopped</span>
            </div>
            <div class="status-item">
                <span class="status-label">Strategy:</span>
                <span class="status-value">Buy at $10.00 → Sell at $10.50</span>
            </div>
            <div class="status-item">
                <span class="status-label">Current Order:</span>
                <span class="status-value" id="orderStatus">None</span>
            </div>
            <div class="status-item" id="orderDetails" style="display:none;">
                <span class="status-label">Order ID / Entry:</span>
                <span class="status-value" id="orderInfo"></span>
            </div>
        </div>
        
        <div class="alert">
            💡 <strong>Demo Mode:</strong> Prices are simulated. This bot demonstrates the strategy without real money.
        </div>
    </div>
    
    <script>
        async function callApi(endpoint) {
            const response = await fetch(endpoint);
            const data = await response.json();
            
            if (endpoint === '/start') {
                document.getElementById('botStatus').innerText = 'Running';
            } else if (endpoint === '/stop') {
                document.getElementById('botStatus').innerText = 'Stopped';
                document.getElementById('orderStatus').innerText = 'None';
                document.getElementById('orderDetails').style.display = 'none';
            } else if (endpoint === '/orders' && data.order_id) {
                document.getElementById('orderStatus').innerText = 'OPEN';
                document.getElementById('orderInfo').innerHTML = `#${data.order_id} @ $${data.entry_price}`;
                document.getElementById('orderDetails').style.display = 'flex';
            } else if (endpoint === '/orders' && !data.order_id) {
                document.getElementById('orderStatus').innerText = 'None';
                document.getElementById('orderDetails').style.display = 'none';
            } else if (endpoint === '/take_profit') {
                document.getElementById('orderStatus').innerText = 'Closed - Profit Taken';
                document.getElementById('orderDetails').style.display = 'none';
                setTimeout(() => {
                    if (document.getElementById('botStatus').innerText !== 'Running') {
                        document.getElementById('orderStatus').innerText = 'None';
                    }
                }, 3000);
            }
        }
        
        async function updatePrice() {
            const response = await fetch('/price');
            const data = await response.json();
            document.getElementById('price').innerHTML = `$${data.price.toFixed(2)}`;
            
            if (data.price <= 10.00) {
                document.getElementById('change').innerHTML = '📉 Price is low - BUY signal!';
                document.getElementById('change').style.color = '#10b981';
            } else if (data.price >= 10.50) {
                document.getElementById('change').innerHTML = '📈 Price is high - SELL signal!';
                document.getElementById('change').style.color = '#ef4444';
            } else {
                document.getElementById('change').innerHTML = 'Waiting for price to reach $10.00 or $10.50...';
                document.getElementById('change').style.color = '#666';
            }
        }
        
        setInterval(updatePrice, 2000);
        setInterval(() => callApi('/orders'), 3000);
        updatePrice();
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
