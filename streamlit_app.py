import streamlit as st
import ccxt
import numpy as np
import requests
import time
import pandas as pd
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="MASTER v1.5.1 MOBILE", layout="centered")

# Telegram-asetukset (Samat kuin työpöytäversiossa)
T_TOKEN = "8098520195:AAFCpGPgYzwgMYs7v2WF-XegjunKyK7x04M"
T_ID = "1388229604"
exchange = ccxt.bitstamp({'enableRateLimit': True})

def laheta_telegram(msg):
    try:
        requests.get(f"https://api.telegram.org/bot{T_TOKEN}/sendMessage", 
                     params={"chat_id": T_ID, "text": msg, "parse_mode": "Markdown"}, timeout=5)
    except: pass

# --- SESSION STATE (Saldon ja lokien säilytys) ---
if 'kassa' not in st.session_state:
    st.session_state.kassa = 1000.0
    st.session_state.btc = 0.0
    st.session_state.max_val = 1000.0
    st.session_state.logs = []

# --- ANALYYSIFUNKTIO ---
def aja_analyysi():
    try:
        ticker = exchange.fetch_ticker('BTC/EUR')
        hinta = float(ticker['last'])
        
        # RSI-laskenta (1min kynttilät)
        ohlcv = exchange.fetch_ohlcv('BTC/EUR', timeframe='1m', limit=21)
        closes = np.array([x[4] for x in ohlcv])
        deltas = np.diff(closes)
        up = deltas[deltas >= 0].sum() / 14 if any(deltas >= 0) else 0.001
        down = -deltas[deltas < 0].sum() / 14 if any(deltas < 0) else 0.001
        rsi = 100 - (100 / (1 + (up/down)))
        
        return hinta, rsi
    except:
        return None, None

# --- UI ALKU ---
st.title("🚀 MASTER v1.5.1")

# Sivupalkki asetuksille
st.sidebar.header("Hallintapaneeli")
alkusaldo = st.sidebar.number_input("Aseta alkukassa (€)", value=1000.0)
if st.sidebar.button("Nollaa ja Resetoi"):
    st.session_state.kassa = alkusaldo
    st.session_state.btc = 0.0
    st.session_state.max_val = alkusaldo
    st.session_state.logs = []
    st.rerun()

panos_eur = st.sidebar.slider("Automaattipanos (€)", 10, 2000, 500)
botti_on = st.sidebar.toggle("AUTO-BOT AKTIIVINEN", value=False)

# --- BOTIN AJAMINEN ---
hinta, rsi = aja_analyysi()

if hinta:
    # 1. Stop-Loss tarkistus (-3%)
    salkku_nyt = st.session_state.kassa + (st.session_state.btc * hinta)
    if salkku_nyt > st.session_state.max_val:
        st.session_state.max_val = salkku_nyt
    
    lasku = (salkku_nyt / st.session_state.max_val) - 1
    if lasku <= -0.03 and st.session_state.btc > 0.000001:
        myynti_eur = st.session_state.btc * hinta * 0.996
        st.session_state.kassa += myynti_eur
        st.session_state.btc = 0.0
        st.session_state.logs.insert(0, f"🚨 STOP-LOSS! Myyty kaikki @ {hinta:.0f}€")
        laheta_telegram("🚨 *STOP-LOSS LAUKESI PUHELIMESSA! Salkku suojattu.*")

    # 2. Automaattiset kaupat
    if botti_on:
        if rsi < 31 and st.session_state.kassa >= panos_eur:
            st.session_state.btc += (panos_eur / hinta)
            st.session_state.kassa -= (panos_eur * 1.004)
            st.session_state.logs.insert(0, f"🟢 OSTO (BOT): {panos_eur}€ @ {hinta:.0f}€")
            laheta_telegram(f"🟢 OSTO: {panos_eur}€")
        
        elif rsi > 69 and st.session_state.btc > 0.000001:
            # Trailing: myy 30%
            myynti_btc = st.session_state.btc * 0.3
            myynti_eur = myynti_btc * hinta * 0.996
            st.session_state.btc -= myynti_btc
            st.session_state.kassa += myynti_eur
            st.session_state.logs.insert(0, f"🔴 MYYNTI (30% BOT): {myynti_eur:.2f}€ @ {hinta:.0f}€")
            laheta_telegram(f"🔴 MYYNTI (30%): {myynti_eur:.2f}€")

    # --- NÄYTTÖMETRIIKAT ---
    c1, c2 = st.columns(2)
    c1.metric("BTC HINTA", f"{hinta:,.2f} €")
    c2.metric("RSI (1min)", f"{rsi:.1f}")

    st.write("### Salkun tila")
    m1, m2, m3 = st.columns(3)
    m1.metric("Käteinen", f"{st.session_state.kassa:.2f} €")
    m2.metric("BTC", f"{st.session_state.btc:.5f}")
    m3.metric("Yhteensä", f"{salkku_nyt:.2f} €", f"{salkku_nyt - alkusaldo:.2f} €")

    st.divider()

    # --- MANUAALINEN HALLINTA (Päivitetty) ---
    st.subheader("Manuaalinen Ohjaus 🕹️")
    
    col_buy, col_sell = st.columns(2)

    with col_buy:
        summa = st.number_input("Osta summalla (€)", min_value=10.0, value=100.0, step=50.0)
        if st.button("↑ OSTA NYT", use_container_width=True, type="primary"):
            if st.session_state.kassa >= summa:
                st.session_state.btc += (summa / hinta)
                st.session_state.kassa -= (summa * 1.004)
                st.session_state.logs.insert(0, f"🔵 MANUAALINEN OSTO: {summa}€")
                laheta_telegram(f"🔵 MANUAALINEN OSTO: {summa}€")
                st.rerun()
            else:
                st.error("Ei tarpeeksi käteistä!")

    with col_sell:
        prosentti = st.slider("Myy % määrästä", 0, 100, 100)
        if st.button("↓ MYY VALITTU", use_container_width=True):
            if st.session_state.btc > 0:
                myynti_btc = st.session_state.btc * (prosentti / 100)
                myynti_eur = myynti_btc * hinta * 0.996
                st.session_state.btc -= myynti_btc
                st.session_state.kassa += myynti_eur
                st.session_state.logs.insert(0, f"⚪ MANUAALINEN MYYNTI: {prosentti}%")
                laheta_telegram(f"⚪ MANUAALINEN MYYNTI: {prosentti}%")
                st.rerun()

    st.divider()
    st.subheader("Tapahtumaloki")
    for log in st.session_state.logs[:8]:
        st.write(log)

# Automaattinen päivitys (sivu latautuu uudelleen 10s välein)
time.sleep(10)
st.rerun()
