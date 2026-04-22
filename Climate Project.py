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
    asset_type = st.radio("Asset Type:", ["Equity (หุ้นรายตัว)", "Mutual Fund (กองทุน)"], key="asset_type_select")
    
    # ส่วนรับค่า Ticker พร้อมระบบแนะนำ Proxy
    ticker_input = st.text_input("Ticker (เช่น PTT.BK หรือชื่อกองทุน):", "PTT.BK", key="main_ticker_input")
    
    use_proxy = st.checkbox("ใช้ดัชนีตัวแทน (Proxy) สำหรับกองทุน", value=(asset_type == "Mutual Fund (กองทุน)"))
    
    if use_proxy:
        proxy_choice = st.selectbox("เลือกดัชนีที่ตรงกับกองทุนของคุณ:", 
                                   ["^GSPC (S&P 500 - สำหรับ SCBS&P500)", 
                                    "^SET.BK (ดัชนีหุ้นไทยรวม)", 
                                    "SET50.BK (หุ้นไทย 50 ตัวใหญ่)", 
                                    "^IXIC (Nasdaq - หุ้นเทคโนโลยี)"], key="proxy_select")
        # ดึงเฉพาะ Ticker ออกมาจากวงเล็บ
        ticker = proxy_choice.split(" ")[0]
        st.caption(f"💡 ระบบจะใช้ {ticker} เป็นตัวแทนในการคำนวณความเสี่ยงภูมิอากาศ")
    else:
        ticker = ticker_input

    # ... (ส่วน Sector และ Scenario อื่นๆ คงเดิม) ...
# --- CORE LOGIC ---
@st.cache_data(ttl=3600)
def fetch_and_model(symbol):
    try:
        # ดึงข้อมูล Ticker เป้าหมาย + Proxy สำหรับคำนวณ Carbon Beta
        data = yf.download([symbol, BROWN_PROXY, GREEN_PROXY, SET_INDEX], 
                           start="2022-01-01", progress=False)['Close']
        
        # ตรวจสอบว่ามีข้อมูล Ticker นั้นจริงหรือไม่
        if symbol not in data.columns or data[symbol].isnull().all():
            return None, None
            
        returns = data.pct_change().dropna()
        
        # Modeling: Transition Risk Sensitivity (Carbon Beta)
        bmg_factor = returns[BROWN_PROXY] - returns[GREEN_PROXY]
        Y = returns[symbol]
        X = pd.DataFrame({'Market': returns[SET_INDEX], 'Carbon_Factor': bmg_factor})
        X = sm.add_constant(X)
        model = sm.OLS(Y, X).fit()
        
        return model, data[symbol].iloc[-1]
    except Exception:
        return None, None

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
