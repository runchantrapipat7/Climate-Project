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

# --- CSS Custom Styling (Fixed Contrast) ---
st.markdown("""
    <style>
    [data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        padding: 15px; border-radius: 10px; border: 1px solid rgba(128, 128, 128, 0.2);
    }
    [data-testid="stMetricValue"] > div { color: #2ECC71 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
st.title("📊 Climate Risk Modeling & Sustainable Finance Dashboard")
st.markdown("### Strategic Integration of Environmental Risks into Asset Valuation")

# --- SIDEBAR: ASSET SELECTION ---
with st.sidebar:
    st.header("📌 Asset Selection")
    # เพิ่ม key="unique_id" เพื่อป้องกัน Duplicate Element ID
    asset_type = st.radio("Asset Type:", ["Equity (หุ้นรายตัว)", "Mutual Fund (กองทุน)"], key="asset_type_select")
    ticker = st.text_input("Ticker (e.g. PTT.BK or BTP.BK):", "PTT.BK", key="main_ticker_input")
    
    sector = st.selectbox("Sector:", ["Energy", "Manufacturing", "Banking", "Agriculture", "Others"], key="sector_select")
    
    st.divider()
    st.header("🌡️ Climate Scenarios (TCFD)")
    scenario = st.select_slider("Scenario Ambition:", 
                               options=["1.5°C (Aggressive Tax)", "2.0°C (Moderate Tax)", "NZA (Business as Usual)"],
                               key="scenario_slider")
    
    tax_map = {"1.5°C (Aggressive Tax)": 1500, "2.0°C (Moderate Tax)": 600, "NZA (Business as Usual)": 200}
    current_tax = tax_map[scenario]
    
    st.divider()
    st.header("💰 Financial Parameters")
    emissions = st.number_input("Emissions (tCO2e):", value=500000, key="em_input")
    market_cap = st.number_input("Market Value / Cap (Million THB):", value=100000, key="mkt_cap_input")
    wacc = st.slider("WACC (%):", 5.0, 15.0, 8.0, key="wacc_slider") / 100

# --- CORE LOGIC ---
@st.cache_data(ttl=3600)
def fetch_and_model(symbol):
    data = yf.download([symbol, BROWN_PROXY, GREEN_PROXY, SET_INDEX], start="2022-01-01")['Close']
    returns = data.pct_change().dropna()
    bmg_factor = returns[BROWN_PROXY] - returns[GREEN_PROXY]
    Y = returns[symbol]
    X = pd.DataFrame({'Market': returns[SET_INDEX], 'Carbon_Factor': bmg_factor})
    X = sm.add_constant(X)
    model = sm.OLS(Y, X).fit()
    return model, data[symbol].iloc[-1]

try:
    model, last_price = fetch_and_model(ticker)
    carbon_beta = model.params['Carbon_Factor']
    
    # CALCULATIONS
    carbon_liability = emissions * current_tax
    valuation_loss = (carbon_liability / wacc) / 1_000_000 # In Million THB
    
    # DISPLAY METRICS
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Price", f"{last_price:,.2f} THB")
    c2.metric("Carbon Beta", f"{carbon_beta:.3f}")
    c3.metric("Projected Tax", f"{current_tax} THB/t")
    c4.metric("Market Beta", f"{model.params['Market']:.2f}")

    st.divider()

    # WATERFALL CHART
    st.subheader(f"Equity Value Bridge: {asset_type}")
    fig = go.Figure(go.Waterfall(
        orientation = "v",
        measure = ["relative", "relative", "total"],
        x = ["Original Value", "Climate Risk Impact", "Adjusted Value"],
        y = [market_cap, -valuation_loss, market_cap - valuation_loss],
        connector = {"line":{"color":"rgb(63, 63, 63)"}},
    ))
    st.plotly_chart(fig, use_container_width=True)
    
    st.info(f"**Sustainable Finance Insight:** ความเสี่ยง {scenario} ส่งผลให้มูลค่าลดลง { (valuation_loss/market_cap)*100:.2f}%")

except Exception as e:
    st.error(f"กรุณาตรวจสอบ Ticker: {e}")
