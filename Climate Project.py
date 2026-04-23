import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Sustainable Finance AI", layout="wide")

# --- CSS: Fixed Contrast & Professional Theme ---
st.markdown("""
    <style>
    [data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        padding: 20px; border-radius: 15px; border: 1px solid rgba(128, 128, 128, 0.2);
    }
    [data-testid="stMetricValue"] > div { color: #2ECC71 !important; }
    .stAlert { border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Risk Controller")
    asset_class = st.radio("Asset Class", ["Equity", "Mutual Fund"], horizontal=True)
    ticker_input = st.text_input("Symbol Ticker (เช่น PTT.BK, CPALL.BK)", "PTT.BK")
    
    st.divider()
    st.header("🌍 Scenario Analysis (TCFD)")
    scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
    tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    st.divider()
    st.header("🌊 Physical Risk Score")
    flood_risk = st.slider("Flood Exposure (%)", 0, 100, 45)
    drought_risk = st.slider("Drought Exposure (%)", 0, 100, 30)

# --- CORE LOGIC: CLIMATE MODELING ---
@st.cache_data(ttl=3600)
def run_full_analysis(symbol):
    try:
        # ดึงข้อมูล Ticker และตัวแทนตลาด
        data = yf.download([symbol, "PTTEP.BK", "EA.BK", "^SET.BK"], start="2023-01-01", progress=False)['Close']
        if symbol not in data.columns or data[symbol].isnull().all():
            return None, None, None, None
            
        returns = data.pct_change().dropna()
        # คำนวณ Carbon Beta (BMG)
        bmg = returns["PTTEP.BK"] - returns["EA.BK"]
        X = sm.add_constant(pd.DataFrame({'Market': returns["^SET.BK"], 'Carbon': bmg}))
        model = sm.OLS(returns[symbol], X).fit()
        
        # ดึงข่าว (แยก try-except เพื่อไม่ให้แอปพังถ้าไม่มีข่าว)
        try:
            news = yf.Ticker(symbol).news[:5]
        except:
            news = []
            
        return model, data[symbol].iloc[-1], returns[symbol], news
    except:
        return None, None, None, None

# --- MAIN DISPLAY ---
st.title("📊 Climate Risk Modeling & Sustainable Finance")
st.markdown(f"**Strategic Market Intelligence** | Analysis Date: {datetime.now().strftime('%Y-%m-%d')}")

model, price, hist_ret, news_data = run_full_analysis(ticker_input)

if model:
    carbon_beta = model.params['Carbon']
    
    # --- ROW 1: METRICS ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Price", f"{price:,.2f} THB")
    col2.metric("Carbon Beta", f"{carbon_beta:.3f}")
    col3.metric("Projected Carbon Tax", f"{tax_price} / t")
    col4.metric("Market Sensitivity", f"{model.params['Market']:.2f}")

    st.divider()

    # --- ROW 2: CHARTS ---
    l_col, r_col = st.columns([1, 1.5])
    with l_col:
        st.subheader("🔥 Transition Risk Meter")
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number", value = carbon_beta * 100,
            gauge = {'axis': {'range': [-50, 50]}, 'bar': {'color': "#E74C3C" if carbon_beta > 0 else "#2ECC71"}}))
        st.plotly_chart(fig_gauge, use_container_width=True)

    with r_col:
        st.subheader("📈 Physical Risk Matrix")
        risk_df = pd.DataFrame({'Risk': ['Flood', 'Drought', 'Coastal'], 'Score': [flood_risk, drought_risk, flood_risk*0.5]})
        st.plotly_chart(px.bar(risk_df, x='Score', y='Risk', orientation='h', color='Score', color_continuous_scale='Reds'), use_container_width=True)

    # --- ROW 3: RESEARCH & NEWS ---
    st.divider()
    res_col, news_col = st.columns([1, 1])
    
    with res_col:
        st.subheader("🧬 Sustainable Finance Research")
        memo = f"""
