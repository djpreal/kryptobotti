import streamlit as st
import pandas as pd
import ccxt
import time
import threading
import json
import os
import requests
from datetime import datetime
import numpy as np
import plotly.graph_objects as go

# --- CONFIGURATIO ---
STATE_FILE = "state.json"
LOG_FILE = "trades.txt"
T_TOKEN = "8098520195:AAFCpGPgYzwgMYs7v2WF-XegjunKyK7x04M"
T_ID = "1388229604"

exchange = ccxt.bitstamp({'enableRateLimit': True})

class BotEngine:
    def __init__(self):
        self.load_state()
        self.last_price = 0.0
        self.ohlcv_data = [] 
        self.is_running = False
        self.auto_bot = False
        self.commission = 0.004
        
        threading.Thread(target=self.price_loop, daemon=True).start()
        threading.Thread(target=self.logic_loop, daemon=True).start()

    def load_state(self):
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r") as f:
                d = json.load(f)
                self.kassa = d.get("kassa", 1000.0)
                self.btc_amount = d.get("btc", 0.0)
                self.alkukassa = d.get("alku", 1000.0)
        else:
            self.kassa = 1000.0; self.btc_amount = 0.0; self.alkukassa = 1000.0

    def save_state(self):
        with open(STATE_FILE, "w") as f:
            json.dump({"kassa": self.kassa, "btc": self.btc_amount, "alku": self.alkukassa}, f)

    def log_trade(self, msg):
        with open(LOG_FILE, "a") as f:
            f.write(f"{datetime.now().strftime('%H:%M:%S')} - {msg}\n")

    def price_loop(self):
        while True:
            try:
                # Haetaan kynttilädata (1 min välein)
                data = exchange.fetch_ohlcv('BTC/EUR', timeframe='1m', limit=30)
                self.ohlcv_data = data
                self.last_price = data[-1][4]
            except: pass
            time.sleep(10)

    def execute_trade(self, mode, amount_eur, source="BOTTI"):
        if self.last_price <= 0: return
        if mode == "buy":
            cost = amount_eur * (1 + self.commission)
            if self.kassa >= cost:
                bought_btc = amount_eur / self.last_price
                self.kassa -= cost
                self.btc_amount += bought_btc
                self.save_state()
                msg = f"🟢 OSTETTU: {amount_eur}€ ({source})"
                self.log_trade(msg)
            else: st.error("Ei tarpeeksi käteistä!")
        elif mode == "sell":
            current_btc_val = self.btc_amount * self.last_price
            sell_eur = min(amount_eur, current_btc_val)
            if sell_eur > 1.0:
                sold_btc = sell_eur / self.last_price
                net_cash = sell_eur * (1 - self.commission)
                self.btc_amount -= sold_btc
                self.kassa += net_cash
                self.save_state()
                msg = f"🔴 MYYTY: {sell_eur:.2f}€ ({source})"
                self.log_trade(msg)

    def logic_loop(self):
        while True:
            if self.is_running and self.auto_bot and self.last_price > 0:
                try:
                    closes = np.array([x[4] for x in self.ohlcv_data])
                    deltas = np.diff(closes)
                    up = deltas[deltas >= 0].sum() / 14 if any(deltas >= 0) else 0.1
                    down = -deltas[deltas < 0].sum() / 14 if any(deltas < 0) else 0.1
                    rsi = 100 - (100 / (1 + (up/down)))
                    if rsi < 30: self.execute_trade("buy", 500, "AUTO-RSI")
                    elif rsi > 70: self.execute_trade("sell", 500, "AUTO-RSI")
                except: pass
            time.sleep(30)

# --- UI ---
st.set_page_config(page_title="KRYPTO BOTTI PRO", layout="wide")

if 'bot' not in st.session_state:
    st.session_state.bot = BotEngine()

bot = st.session_state.bot

# Lasketaan arvot
total_val = bot.kassa + (bot.btc_amount * bot.last_price)
profit_pct = ((total_val / bot.alkukassa) - 1) * 100

# Banneri ja Metrics
st.title("₿ PERTUN KRYPTO BOTTI v1.6.5")
m1, m2, m3, m4 = st.columns(4)
m1.metric("BTC HINTA", f"{bot.last_price:,.2f} €")
m2.metric("SALKKU YHTEENSÄ", f"{total_val:,.2f} €", f"{profit_pct:+.2f} %")
m3.metric("KÄTEINEN", f"{bot.kassa:,.2f} €")
m4.metric("BTC OMISTUS", f"{bot.btc_amount:.6f}")

# Kynttiläkaavio
if bot.ohlcv_data:
    df = pd.DataFrame(bot.ohlcv_data, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    
    fig = go.Figure(data=[go.Candlestick(x=df['ts'],
                open=df['open'], high=df['high'],
                low=df['low'], close=df['close'],
                increasing_line_color= '#22C55E', decreasing_line_color= '#EF4444')])
    
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, b=0, t=0))
    st.plotly_chart(fig, use_container_width=True)

# Ohjaimet
st.sidebar.header("BOTIN HALLINTA")
bot.is_running = st.sidebar.toggle("Seuranta Päällä", value=bot.is_running)
bot.auto_bot = st.sidebar.toggle("RSI Automatiikka", value=bot.auto_bot)

trade_amount = st.sidebar.slider("Kauppasumma (€)", 10, 2000, 500)
if st.sidebar.button("↑ OSTA", use_container_width=True):
    bot.execute_trade("buy", trade_amount, "MANUAL")
if st.sidebar.button("↓ MYY", use_container_width=True):
    bot.execute_trade("sell", trade_amount, "MANUAL")

# Loki
with st.expander("Näytä kauppahistoria"):
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            st.text("".join(f.readlines()[-15:]))

if bot.is_running:
    time.sleep(10)
    st.rerun()
