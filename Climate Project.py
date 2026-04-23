import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Climate Finance Intelligence", layout="wide")

# --- CSS: High-Contrast Dashboard Style ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px; border-radius: 12px;
    }
    [data-testid="stMetricValue"] > div { color: #2ECC71 !important; font-size: 24px; }
    .stInfo { border-radius: 15px; background-color: rgba(46, 204, 113, 0.1); border: none; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Risk Controller")
    ticker_input = st.text_input("Symbol Ticker (เช่น PTT.BK, CPALL.BK, DELTA.BK)", "PTT.BK")
    
    st.divider()
    st.header("🌍 Scenario & Policy")
    scenario = st.select_slider("Climate Ambition", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
    tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    st.divider()
    st.header("🌊 Physical Risk Score")
    flood_risk = st.slider("Flood Exposure (%)", 0, 100, 45)
    drought_risk = st.slider("Drought Exposure (%)", 0, 100, 30)
    wacc = st.slider("Discount Rate (WACC %)", 5.0, 15.0, 8.0) / 100

# --- CORE LOGIC: DATA ENGINE ---
@st.cache_data(ttl=3600)
def fetch_comprehensive_data(symbol):
    try:
        t_obj = yf.Ticker(symbol)
        # 1. ข้อมูลราคาและ Modeling
        data = yf.download([symbol, "PTTEP.BK", "EA.BK", "^SET.BK"], start="2023-01-01", progress=False)['Close']
        if symbol not in data.columns: return None
        
        returns = data.pct_change().dropna()
        bmg = returns["PTTEP.BK"] - returns["EA.BK"]
        X = sm.add_constant(pd.DataFrame({'Market': returns["^SET.BK"], 'Carbon': bmg}))
        model = sm.OLS(returns[symbol], X).fit()
        
        # 2. ข้อมูลพื้นฐาน (Fundamentals)
        info = t_obj.info
        
        return {
            "model": model,
            "last_price": data[symbol].iloc[-1],
            "history": data[symbol],
            "info": info,
            "news": t_obj.news[:5]
        }
    except: return None

# --- MAIN DISPLAY ---
st.title("🏛️ Sustainable Finance & Climate Risk Intelligence")
st.markdown(f"**Asset Intelligence Terminal** | {ticker_input} | {datetime.now().strftime('%d %B %Y')}")

res = fetch_comprehensive_data(ticker_input)

if res:
    info = res['info']
    model = res['model']
    c_beta = model.params['Carbon']
    
    # --- ROW 1: REAL-TIME FUNDAMENTALS ---
    st.subheader("📌 Corporate Snapshot")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Market Price", f"{res['last_price']:.2f} THB")
    c2.metric("P/E Ratio", f"{info.get('trailingPE', 'N/A')}")
    c3.metric("Div. Yield", f"{info.get('dividendYield', 0)*100:.2f}%")
    c4.metric("Market Cap", f"{info.get('marketCap', 0)/1e9:.1f}B")
    c5.metric("52W High", f"{info.get('fiftyTwoWeekHigh', 0):.2f}")

    st.divider()

    # --- ROW 2: PRICE MOMENTUM & CLIMATE MODELING ---
    col_l, col_r = st.columns([2, 1])
    
    with col_l:
        st.subheader("📈 1-Year Price Momentum")
        fig_price = px.line(res['history'], color_discrete_sequence=['#2ECC71'])
        fig_price.update_layout(xaxis_title="", yaxis_title="Price (THB)", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_price, use_container_width=True)
    
    with col_r:
        st.subheader("🔥 Carbon Sensitivity")
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number", value = c_beta * 100,
            title = {'text': "Carbon Beta Index"},
            gauge = {'axis': {'range': [-50, 50]}, 'bar': {'color': "#E74C3C" if c_beta > 0 else "#2ECC71"}}))
        fig_gauge.update_layout(height=300, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_gauge, use_container_width=True)

    # --- ROW 3: DEEP RESEARCH & RISK ANALYSIS ---
    st.divider()
    res_l, res_r = st.columns([1, 1])
    
    with res_l:
        st.subheader("🧬 Sustainable Finance Research Memo")
        val_impact = (tax_price * 1000) / wacc / 1e6 # Simulation
        memo = f"""
        **วิเคราะห์พื้นฐานรายวัน:**
        บริษัท {info.get('longName', ticker_input)} ดำเนินธุรกิจในกลุ่ม {info.get('sector', 'N/A')} 
        ปัจจุบันมีค่า Carbon Beta ที่ **{c_beta:.3f}** ซึ่งสะท้อนความเสี่ยง {('สูง' if c_beta > 0 else 'ต่ำ')} ต่อการเปลี่ยนผ่านนโยบายคาร์บอน
        
        **Climate Valuation Impact:**
        - ภายใต้ฉากทัศน์ **{scenario}** ที่ราคาภาษี {tax_price} บาท/ตัน
        - คาดการณ์มูลค่ากิจการที่ลดลง (Climate Discount): **-{val_impact:,.2f} Million THB**
        - ความเสี่ยงกายภาพ: **{flood_risk}% Flood Exposure** อิงจากข้อมูลความเสี่ยงลุ่มแม่น้ำเจ้าพระยา
        """
        st.info(memo)
        
        # Waterfall Chart
        fig_water = go.Figure(go.Waterfall(
            x = ["Market Cap", "Climate Loss", "Fair Value"],
            y = [info.get('marketCap', 1e9)/1e6, -val_impact, (info.get('marketCap', 1e9)/1e6) - val_impact],
            measure = ["relative", "relative", "total"]
        ))
        fig_water.update_layout(title="Equity Value Bridge (Million THB)")
        st.plotly_chart(fig_water, use_container_width=True)

    with res_r:
        st.subheader("📰 Daily Market Intelligence & ESG News")
        if res['news']:
            for n in res['news']:
                title = n.get('title', 'N/A')
                pub = n.get('publisher', 'Unknown')
                link = n.get('link', '#')
                st.write(f"**[{pub}]** - {title}")
                st.write(f"[อ่านต่อ]({link})")
                st.divider()
        else:
            st.warning("ไม่มีข้อมูลข่าวสารล่าสุดในระบบสำหรับหุ้นตัวนี้")

else:
    st.error(f"❌ ไม่พบข้อมูลสำหรับ Ticker: {ticker_input}")
    st.info("💡 กรุณาตรวจสอบว่าชื่อหุ้นถูกต้องและลงท้ายด้วย .BK (เช่น PTT.BK)")
