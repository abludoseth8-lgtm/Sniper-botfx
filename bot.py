import os
import time
import requests
from binance.client import Client
from datetime import datetime

# Keys from environment variables
API_KEY = os.environ.get('API_KEY')
API_SECRET = os.environ.get('API_SECRET')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

# Binance testnet client
client = Client(API_KEY, API_SECRET, testnet=True)

SYMBOL = 'BTCUSDT'
QUANTITY = 0.001
journal = []

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except:
        pass

def get_rsi(period=14):
    klines = client.get_klines(
        symbol=SYMBOL,
        interval=Client.KLINE_INTERVAL_5MINUTE,
        limit=period+1
    )
    closes = [float(k[4]) for k in klines]
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

def get_price():
    ticker = client.get_symbol_ticker(symbol=SYMBOL)
    return float(ticker['price'])

def place_order(side, price):
    try:
        order = client.create_order(
            symbol=SYMBOL,
            side=side,
            type=Client.ORDER_TYPE_MARKET,
            quantity=QUANTITY
        )
        sl = price * 0.998 if side == 'BUY' else price * 1.002
        tp = price * 1.002 if side == 'BUY' else price * 0.998
        msg = f"""
🚨 NEW TRADE - BTCUSDT
Direction: {side}
Entry: ${price:,.2f}
Stop Loss: ${sl:,.2f}
Take Profit: ${tp:,.2f}
Time: {datetime.now().strftime('%H:%M:%S')}
        """
        send_telegram(msg)
        journal.append({
            'side': side,
            'entry': price,
            'sl': sl,
            'tp': tp,
            'time': str(datetime.now())
        })
        return order
    except Exception as e:
        send_telegram(f"Order failed: {e}")
        return None

def check_signal():
    rsi = get_rsi()
    price = get_price()
    print(f"RSI: {rsi} | Price: {price}")
    if rsi <= 30:
        send_telegram(f"RSI oversold: {rsi}\nLooking to BUY...")
        place_order('BUY', price)
    elif rsi >= 70:
        send_telegram(f"RSI overbought: {rsi}\nLooking to SELL...")
        place_order('SELL', price)

def send_journal():
    if not journal:
        send_telegram("Journal: No trades yet today")
        return
    msg = "DAILY JOURNAL\n"
    msg += f"Total trades: {len(journal)}\n"
    for t in journal:
        msg += f"\n{t['side']} @ ${t['entry']:,.2f}"
    send_telegram(msg)

send_telegram("Mamba Bot is LIVE! Watching BTCUSDT...")

while True:
    try:
        check_signal()
        time.sleep(300)
    except Exception as e:
        send_telegram(f"Bot error: {e}")
        time.sleep(60)
