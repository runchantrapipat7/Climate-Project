import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Climate Risk Intelligence", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS (Glassmorphism Style) ---
st.markdown("""
    <style>
    .main { background: linear-gradient(180deg, #0e1117 0%, #161b22 100%); }
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px; border-radius: 15px;
    }
    .stButton>button {
        width: 100%; border-radius: 10px; background: #2ECC71; color: white; height: 3em;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: ASSET & RISK PARAMETERS ---
with st.sidebar:
    st.title("🛡️ Risk Control")
    asset_type = st.radio("Asset Class", ["Equity", "Mutual Fund"], horizontal=True)
    ticker_input = st.text_input("Symbol Ticker", "PTT.BK")
    
    st.divider()
    st.header("🌍 Climate Scenario")
    scenario = st.select_slider("Policy Ambition", options=["Net Zero 2050", "Late Transition", "Current Policy"])
    tax_price = {"Net Zero 2050": 1500, "Late Transition": 800, "Current Policy": 200}[scenario]
    
    st.divider()
    st.header("🌊 Physical Risk Score")
    flood_risk = st.slider("Flood Exposure (0-100)", 0, 100, 45)
    drought_risk = st.slider("Drought Exposure (0-100)", 0, 100, 30)

# --- CORE FUNCTIONS ---
@st.cache_data(ttl=3600)
def get_analysis_data(symbol):
    try:
        # ดึงข้อมูลหุ้น และ Proxy (PTTEP=Brown, EA=Green)
        data = yf.download([symbol, "PTTEP.BK", "EA.BK", "^SET.BK"], start="2023-01-01", progress=False)['Close']
        returns = data.pct_change().dropna()
        # คำนวณ Carbon Beta
        bmg = returns["PTTEP.BK"] - returns["EA.BK"]
        model = sm.OLS(returns[symbol], sm.add_constant(pd.DataFrame({'Mkt': returns["^SET.BK"], 'Carbon': bmg}))).fit()
        return model, data[symbol].iloc[-1], returns[symbol]
    except: return None, None, None

# --- MAIN DASHBOARD ---
st.title("🌍 Climate Risk Modeling & Sustainable Finance")
st.markdown(f"**Market Intelligence Terminal** | Analysis Date: {datetime.now().strftime('%Y-%m-%d')}")

model, price, hist_ret = get_analysis_data(ticker_input)

if model:
    c_beta = model.params['Carbon']
    
    # --- ROW 1: KEY PERFORMANCE INDICATORS ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Market Price", f"{price:,.2f} THB")
    col2.metric("Carbon Beta", f"{c_beta:.3f}")
    col3.metric("Est. Carbon Tax", f"{tax_price} / t")
    col4.metric("Risk-Adjusted P/E", "14.2x", delta="-1.5x", delta_color="inverse")

    st.divider()

    # --- ROW 2: RISK GAUGES & CHARTS ---
    left_col, right_col = st.columns([1, 2])
    
    with left_col:
        st.subheader("🌡️ Climate Risk Meter")
        # Gauge Chart
        risk_val = abs(c_beta * 100)
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = risk_val,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Transition Risk Level", 'font': {'size': 18}},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "#2ECC71" if c_beta < 0 else "#E74C3C"},
                'steps': [
                    {'range': [0, 30], 'color': "rgba(46, 204, 113, 0.2)"},
                    {'range': [30, 70], 'color': "rgba(241, 196, 15, 0.2)"},
                    {'range': [70, 100], 'color': "rgba(231, 76, 60, 0.2)"}]
            }))
        fig_gauge.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_gauge, use_container_width=True)

    with right_col:
        st.subheader("📈 Performance vs Climate Sensitivity")
        fig_line = px.area(hist_ret.cumsum(), labels={'value': 'Cumulative Return', 'Date': ''}, color_discrete_sequence=['#2ECC71'])
        fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300)
        st.plotly_chart(fig_line, use_container_width=True)

    # --- ROW 3: PHYSICAL RISK & SUSTAINABLE FINANCE ---
    st.divider()
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("🌊 Physical Risk Matrix (Thailand Focus)")
        # จำลองข้อมูลความเสี่ยงรายพื้นที่
        risk_df = pd.DataFrame({
            'Risk Type': ['Inland Flood', 'Coastal Flood', 'Water Stress', 'Heat Wave'],
            'Impact Score': [flood_risk, flood_risk*0.6, drought_risk, 20]
        })
        fig_bar = px.bar(risk_df, x='Impact Score', y='Risk Type', orientation='h', color='Impact Score', color_continuous_scale='Reds')
        st.plotly_chart(fig_bar, use_container_width=True)
        st.caption("อิงจากโมเดลความเสี่ยงในไทย: 95% ของภัยพิบัติคืออุทกภัย ซึ่งกระทบพื้นที่ลุ่มแม่น้ำเจ้าพระยา (GDP 50% ของประเทศ)")

    with c2:
        st.subheader("💎 Sustainable Finance Valuation")
        # Waterfall Chart
        val_impact = (tax_price * 1000) / 0.08 / 1e6 # Simplified DCF
        fig_water = go.Figure(go.Waterfall(
            orientation = "v",
            measure = ["relative", "relative", "total"],
            x = ["Market Cap", "Climate Discount", "Fair Value"],
            y = [1000, -val_impact, 1000-val_impact],
            connector = {"line":{"color":"#7f8c8d"}},
        ))
        st.plotly_chart(fig_water, use_container_width=True)

else:
    st.warning("🔍 กำลังรอข้อมูลจาก Ticker... หากเป็นกองทุน ให้ลองใส่ Ticker ตัวแทน เช่น ^GSPC (S&P 500) หรือ ^SET.BK")
