import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(page_title="Sustainable Finance Analyzer", layout="wide")
SET_INDEX = "^SET.BK"
BROWN_PROXY = "PTTEP.BK"
GREEN_PROXY = "EA.BK"

# --- CSS Custom Styling ---
st.markdown("""
    <style>
    [data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        padding: 15px; border-radius: 10px; border: 1px solid rgba(128, 128, 128, 0.2);
    }
    [data-testid="stMetricValue"] > div { color: #2ECC71 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Climate Risk Modeling & Sustainable Finance Dashboard")
st.markdown("### Strategic Integration of Environmental Risks into Asset Valuation")

# --- SIDEBAR: ASSET SELECTION ---
with st.sidebar:
    st.header("📌 Asset Selection")
    asset_type = st.radio("Asset Type:", ["Equity (หุ้นรายตัว)", "Mutual Fund (กองทุน)"], key="asset_type")
    
    ticker_input = st.text_input("Ticker (เช่น PTT.BK):", "PTT.BK", key="ticker_input")
    
    # ระบบ Proxy อัตโนมัติสำหรับกองทุน
    use_proxy = st.checkbox("ใช้ดัชนีตัวแทน (Proxy)", value=(asset_type == "Mutual Fund (กองทุน)"))
    
    if use_proxy:
        proxy_choice = st.selectbox("เลือกดัชนีตัวแทน:", 
                                   ["^GSPC (S&P 500 - สำหรับ SCBS&P500)", "^SET.BK (หุ้นไทย)", "SET50.BK (หุ้นใหญ่)"], key="proxy_choice")
        ticker = proxy_choice.split(" ")[0]
    else:
        ticker = ticker_input

    st.divider()
    scenario = st.select_slider("Scenario Ambition:", 
                               options=["1.5°C (Aggressive)", "2.0°C (Moderate)", "NZA (Standard)"], key="sc_slider")
    tax_map = {"1.5°C (Aggressive)": 1500, "2.0°C (Moderate)": 600, "NZA (Standard)": 200}
    current_tax = tax_map[scenario]
    
    emissions = st.number_input("Emissions (tCO2e):", value=500000, key="em")
    market_cap = st.number_input("Market Value (Million THB):", value=100000, key="mcap")
    wacc = st.slider("WACC (%):", 5.0, 15.0, 8.0, key="wacc") / 100

# --- CORE LOGIC ---
@st.cache_data(ttl=3600)
def fetch_and_model(symbol):
    try:
        data = yf.download([symbol, BROWN_PROXY, GREEN_PROXY, SET_INDEX], start="2022-01-01", progress=False)['Close']
        if symbol not in data.columns or data[symbol].isnull().all():
            return None, None
            
        returns = data.pct_change().dropna()
        bmg_factor = returns[BROWN_PROXY] - returns[GREEN_PROXY]
        Y = returns[symbol]
        X = pd.DataFrame({'Market': returns[SET_INDEX], 'Carbon_Factor': bmg_factor})
        X = sm.add_constant(X)
        return sm.OLS(Y, X).fit(), data[symbol].iloc[-1]
    except:
        return None, None

# --- DISPLAY ---
model, last_price = fetch_and_model(ticker)

if model is not None:
    carbon_beta = model.params['Carbon_Factor']
    carbon_liability = emissions * current_tax
    val_loss = (carbon_liability / wacc) / 1_000_000

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Price", f"{last_price:,.2f} THB")
    c2.metric("Carbon Beta", f"{carbon_beta:.3f}")
    c3.metric("Projected Tax", f"{current_tax} THB/t")
    c4.metric("Market Beta", f"{model.params['Market']:.2f}")

    st.divider()
    st.subheader(f"Equity Value Bridge: {ticker}")
    fig = go.Figure(go.Waterfall(
        orientation = "v", measure = ["relative", "relative", "total"],
        x = ["Original Value", "Climate Impact", "Adjusted Value"],
        y = [market_cap, -val_loss, market_cap - val_loss]
    ))
    st.plotly_chart(fig, use_container_width=True)
    st.info(f"**Sustainable Finance Insight:** ความเสี่ยง {scenario} กระทบมูลค่า { (val_loss/market_cap)*100:.2f}%")
else:
    st.error(f"❌ ไม่พบข้อมูลสำหรับ Ticker: {ticker}. หากเป็นกองทุน 'SCBS&P500' กรุณากดเลือก 'ใช้ดัชนีตัวแทน (Proxy)' และเลือก '^GSPC' ครับ")
