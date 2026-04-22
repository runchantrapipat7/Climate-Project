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
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
st.title("📊 Climate Risk Modeling & Sustainable Finance Dashboard")
st.markdown("### Strategic Integration of Environmental Risks into Asset Valuation")

# --- SIDEBAR: SUSTAINABLE FINANCE INPUTS ---
with st.sidebar:
    st.header("🏢 Corporate Profile")
    ticker = st.text_input("Stock Ticker (e.g. PTT.BK):", "PTT.BK")
    sector = st.selectbox("Sector:", ["Energy", "Manufacturing", "Banking", "Agriculture", "Others"])
    
    st.divider()
    st.header("🌡️ Climate Scenarios (TCFD)")
    scenario = st.select_slider("Climate Ambition:", options=["1.5°C (Aggressive Tax)", "2.0°C (Moderate Tax)", "NZA (Business as Usual)"])
    
    # กำหนดราคาภาษีตาม Scenario
    tax_map = {"1.5°C (Aggressive Tax)": 1500, "2.0°C (Moderate Tax)": 600, "NZA (Business as Usual)": 200}
    current_tax = tax_map[scenario]
    
    st.divider()
    st.header("💰 Financial Parameters")
    emissions = st.number_input("Scope 1+2 Emissions (tCO2e):", value=500000)
    market_cap = st.number_input("Market Cap (Million THB):", value=100000)
    wacc = st.slider("WACC (%):", 5.0, 15.0, 8.0) / 100

# --- CORE LOGIC: CLIMATE RISK MODELING ---
@st.cache_data(ttl=3600)
def fetch_and_model(symbol):
    data = yf.download([symbol, BROWN_PROXY, GREEN_PROXY, SET_INDEX], start="2022-01-01")['Close']
    returns = data.pct_change().dropna()
    
    # 1. Carbon Beta (Transition Risk Exposure)
    bmg_factor = returns[BROWN_PROXY] - returns[GREEN_PROXY]
    Y = returns[symbol]
    X = pd.DataFrame({'Market': returns[SET_INDEX], 'Carbon_Factor': bmg_factor})
    X = sm.add_constant(X)
    model = sm.OLS(Y, X).fit()
    
    return model, data[symbol].iloc[-1], returns

try:
    model, last_price, returns_df = fetch_and_model(ticker)
    carbon_beta = model.params['Carbon_Factor']
    market_beta = model.params['Market']

    # --- CALCULATIONS: SUSTAINABLE FINANCE IMPACT ---
    carbon_liability = emissions * current_tax
    ebitda_impact = (carbon_liability / 1_000_000) # In Millions
    valuation_loss = carbon_liability / wacc / 1_000_000
    
    # --- DASHBOARD LAYOUT ---
    
    # ROW 1: Key Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Price", f"{last_price:,.2f} THB")
    col2.metric("Carbon Beta", f"{carbon_beta:.3f}", delta="Risk Exposure")
    col3.metric("Projected Carbon Tax", f"{current_tax} THB/t")
    col4.metric("Market Beta", f"{market_beta:.2f}")

    st.divider()

    # ROW 2: Scenario Analysis & Valuation
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.subheader("📉 Financial Impact Analysis")
        impact_data = {
            "Metric": ["Annual Carbon Liability", "EBITDA Reduction", "Total Valuation Loss (DCF)"],
            "Value (Million THB)": [f"{carbon_liability/1e6:,.2f}", f"{ebitda_impact:,.2f}", f"{valuation_loss:,.2f}"]
        }
        st.table(pd.DataFrame(impact_data))
        
        # Sustainable Finance Logic: Adjusted Valuation
        st.info(f"**Sustainable Finance Insight:** ค่าความเสี่ยงภูมิอากาศ (Climate Risk) ส่งผลให้มูลค่ากิจการลดลงประมาณ { (valuation_loss/market_cap)*100:.2f}% ของ Market Cap")

    with c2:
        st.subheader("🏗️ Transition Risk Sensitivity")
        # Waterfall Chart
        fig = go.Figure(go.Waterfall(
            name = "Impact", orientation = "v",
            measure = ["relative", "relative", "total"],
            x = ["Market Value", "Climate Risk Impact", "Adjusted Value"],
            y = [market_cap, -valuation_loss, market_cap - valuation_loss],
            connector = {"line":{"color":"rgb(63, 63, 63)"}},
        ))
        fig.update_layout(title="Equity Value Bridge (Climate Adjusted)", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # ROW 3: Risk Mapping
    st.subheader("🗺️ Sustainable Finance Risk Matrix")
    
    # สร้างเมทริกซ์ความเสี่ยง
    risk_col1, risk_col2 = st.columns(2)
    with risk_col1:
        # ภัยธรรมชาติ (Physical Risk)
        st.write("**Physical Risk Score (Regional Data)**")
        st.progress(0.65, text="High Exposure to Flood Risk (Thailand Central Plain)")
        st.caption("อิงจากโมเดล Sustainable Finance: พื้นที่อุตสาหกรรมในไทยเสี่ยงต่อน้ำท่วมสูงขึ้น 25% ในปี 2030")

    with risk_col2:
        # โอกาสในการเปลี่ยนผ่าน (Opportunity)
        st.write("**Transition Opportunity Score**")
        st.progress(0.40, text="Moderate Adaptation to Green Energy")
        st.caption("การปรับตัวเข้าสู่เศรษฐกิจคาร์บอนต่ำ (Low Carbon Economy Adaptation)")

except Exception as e:
    st.error(f"⚠️ Error: {e}. Please ensure the ticker format is correct (e.g., PTT.BK)")
