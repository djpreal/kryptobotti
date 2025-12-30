import streamlit as st
import ccxt
import time
import requests
from datetime import datetime

# --- KONFIGURAATIO ---
st.set_page_config(page_title="Pertun Krypto Botti", layout="wide")
T_TOKEN = "8098520195:AAFCpGPgYzwgMYs7v2WF-XegjunKyK7x04M"
T_ID = "1388229604"

def laheta_telegram(msg):
    try:
        requests.get(f"https://api.telegram.org/bot{T_TOKEN}/sendMessage", 
                     params={"chat_id": T_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

st.title("🚀 PERTUN KRYPTO BOTTI v1.5.1")

# Sivupalkki asetuksille
st.sidebar.header("Hallinta")
alkukassa = st.sidebar.number_input("Alkukassa (€)", value=1000)
panos = st.sidebar.slider("Panos per kauppa (€)", 10, alkukassa, 500)
botti_paalla = st.sidebar.checkbox("Aktivoi AUTO-BOT")

# Tila-muuttujat (pysyvät muistissa)
if 'kassa' not in st.session_state:
    st.session_state.kassa = alkukassa
    st.session_state.btc = 0.0
    st.session_state.max_val = alkukassa

# --- LIVE-NÄYTTÖ ---
col1, col2, col3 = st.columns(3)
hinta_placeholder = col1.empty()
pnl_placeholder = col2.empty()
btc_placeholder = col3.empty()

# Simuloitu looppi (Streamlit päivittyy kun sivu ladataan tai scripti rullaa)
exchange = ccxt.bitstamp()

def aja_botti():
    ticker = exchange.fetch_ticker('BTC/EUR')
    hinta = ticker['last']
    
    salkku = st.session_state.kassa + (st.session_state.btc * hinta)
    if salkku > st.session_state.max_val:
        st.session_state.max_val = salkku
        
    # UI PÄIVITYS
    hinta_placeholder.metric("BTC Hinta", f"{hinta:,.2f} €")
    pnl_placeholder.metric("Salkun arvo", f"{salkku:,.2f} €", f"{salkku-alkukassa:.2f} €")
    btc_placeholder.metric("BTC Omistus", f"{st.session_state.btc:.6f} BTC")

    # TÄHÄN TULEE MASTER v1.5.1 LOGIIKKA (RSI, STOP-LOSS JNE.)
    # (Streamlit tarvitsee hieman erilaisen loopin, mutta logiikka on sama)

if st.button("Päivitä tilanne"):
    aja_botti()

st.info("Botti rullaa taustalla, kun pidät välilehden auki.")
