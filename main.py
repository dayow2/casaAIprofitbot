import os
import threading
import time
import random
import logging
from flask import Flask, render_template_string, jsonify, request
import requests

# --- Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- Telegram Config ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')  # Get from BotFather
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')  # Your personal chat ID

# --- Bot State ---
bot_running = False
trading_thread = None
current_order = None
current_price = 10.00
entry_price = 10.00
take_profit_price = 10.50

# --- Send Telegram Message ---
def send_telegram_message(message):
    """Send alert to your Telegram"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials missing")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            logger.info("Telegram message sent")
        else:
            logger.error(f"Telegram error: {response.text}")
    except Exception as e:
        logger.error(f"Failed to send Telegram: {e}")

# --- Simulated Price ---
def simulate_price():
    global current_price
    change = random.uniform(-0.03, 0.03)
    current_price = round(current_price + change, 2)
    if current_price < 9:
        current_price = 9
    if current_price > 11:
        current_price = 11
    return current_price

# --- Trading Logic with Telegram Alerts ---
def place_order():
    global current_order
    current_order = {
        'id': random.randint(10000, 99999),
        'entry_price': current_price,
        'take_profit': take_profit_price,
        'status': 'OPEN'
    }
    msg = f"🟢 <b>BUY ORDER PLACED</b>\n\n💰 Entry: ${current_price}\n🎯 Take Profit: ${take_profit_price}\n📊 Order ID: {current_order['id']}"
    send_telegram_message(msg)
    logger.info(f"BUY ORDER PLACED at ${current_price}")
    return current_order

def close_order():
    global current_order
    if current_order:
        profit = round(take_profit_price - current_order['entry_price'], 2)
        msg = f"✅ <b>POSITION CLOSED - PROFIT TAKEN</b>\n\n💰 Entry: ${current_order['entry_price']}\n📈 Exit: ${take_profit_price}\n💵 Profit: ${profit}"
        send_telegram_message(msg)
        logger.info(f"ORDER CLOSED - Profit: ${profit}")
        current_order = None

def trading_loop():
    global bot_running, current_order
    send_telegram_message("🤖 <b>Trading Bot Started</b>\n\nMonitoring price: Buy at $10.00 → Sell at $10.50")
    
    while bot_running:
        price = simulate_price()
        
        if not current_order and price <= entry_price:
            place_order()
        elif current_order and price >= take_profit_price:
            close_order()
        
        time.sleep(2)
    
    send_telegram_message("🛑 <b>Trading Bot Stopped</b>\n\nNo new trades will be placed.")

# --- Flask Routes ---
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

# --- Telegram Webhook (Optional) ---
@app.route(f'/webhook/{TELEGRAM_TOKEN}', methods=['POST'])
def telegram_webhook():
    """Receive commands from Telegram"""
    data = request.get_json()
    if data and 'message' in data:
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '')
        
        if text == '/start':
            send_message(chat_id, "🤖 <b>Forex Arbitrage Bot</b>\n\nCommands:\n/status - Check bot status\n/start_bot - Start trading\n/stop_bot - Stop trading\n/order - Show current order\n/profit - Take profit now")
        elif text == '/status':
            status = "🟢 Running" if bot_running else "🔴 Stopped"
            send_message(chat_id, f"Bot Status: {status}\nCurrent Price: ${current_price}\nOrder: {'Open' if current_order else 'None'}")
        elif text == '/start_bot':
            start_trading()
            send_message(chat_id, "✅ Trading started!")
        elif text == '/stop_bot':
            stop_trading()
            send_message(chat_id, "🛑 Trading stopped!")
        elif text == '/order':
            if current_order:
                send_message(chat_id, f"📊 Order #{current_order['id']}\nEntry: ${current_order['entry_price']}\nTarget: ${current_order['take_profit']}")
            else:
                send_message(chat_id, "No open orders")
        elif text == '/profit':
            take_profit()
            send_message(chat_id, "💰 Take profit command executed!")
    
    return 'OK', 200

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'})

# --- HTML Template (same as before) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Forex Arbitrage Bot - Telegram Connected</title>
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
        h1 { text-align: center; color: #333; margin-bottom: 10px; }
        .subtitle { text-align: center; color: #666; margin-bottom: 30px; }
        .telegram-badge {
            background: #0088cc;
            color: white;
            text-align: center;
            padding: 10px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        .price-display {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 30px;
        }
        .price-value { font-size: 48px; font-weight: bold; margin: 10px 0; }
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
            transition: transform 0.2s;
        }
        .btn:hover { transform: translateY(-2px); }
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
        .status-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e5e7eb; }
        .status-item:last-child { border-bottom: none; }
        .status-label { font-weight: bold; color: #4b5563; }
        .status-value { color: #1f2937; font-family: monospace; }
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
        <div class="telegram-badge">
            📱 <strong>Telegram Connected</strong> — Control me from your phone!
        </div>
        
        <div class="price-display">
            <div class="price-value" id="price">$10.00</div>
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
                <span class="status-value">Buy $10.00 → Sell $10.50</span>
            </div>
            <div class="status-item">
                <span class="status-label">Current Order:</span>
                <span class="status-value" id="orderStatus">None</span>
            </div>
        </div>
        
        <div class="alert">
            💡 <strong>Telegram Commands:</strong> Send /start, /status, /start_bot, /stop_bot, /order, /profit to your bot!
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
            } else if (endpoint === '/orders' && data.order_id) {
                document.getElementById('orderStatus').innerHTML = `OPEN (#${data.order_id} @ $${data.entry_price})`;
            } else if (endpoint === '/orders' && !data.order_id) {
                document.getElementById('orderStatus').innerText = 'None';
            }
        }
        
        async function updatePrice() {
            const response = await fetch('/price');
            const data = await response.json();
            document.getElementById('price').innerHTML = `$${data.price.toFixed(2)}`;
        }
        
        setInterval(updatePrice, 1000);
        setInterval(() => callApi('/orders'), 3000);
        updatePrice();
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
