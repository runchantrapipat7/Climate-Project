import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.express as px
from datetime import datetime

# --- Settings ---
CARBON_TAX_RATE = 200 # บาทต่อตัน
SET_INDEX = "^SET.BK"
BROWN_PROXY = "PTTEP.BK"
GREEN_PROXY = "EA.BK"

st.set_page_config(page_title="Advanced Climate Risk Engine", layout="wide")

# UI Header
st.title("🌡️ Thai Climate Risk & Valuation Analyzer")
st.markdown("วิเคราะห์ผลกระทบราคาหุ้น/กองทุน จากภาษีคาร์บอนและภัยธรรมชาติแบบครบวงจร")

# --- 1. Sidebar: User Inputs ---
with st.sidebar:
    st.header("📌 Investment Portfolio")
    asset_type = st.radio("ประเภทสินทรัพย์:", ["Stock (หุ้น)", "Mutual Fund (กองทุน)"])
    ticker = st.text_input("ระบุ Ticker (เช่น PTT.BK, BTP.BK):", "PTT.BK")
    
    st.divider()
    st.header("💼 Holding Details")
    shares_owned = st.number_input("จำนวนหุ้น/หน่วยที่ถือ:", value=1000, step=100)
    avg_cost = st.number_input("ราคาต้นทุนเฉลี่ย (บาท):", value=30.0)
    
    st.divider()
    st.header("🌍 Climate Risk Factors")
    emissions = st.number_input("ปริมาณการปล่อยก๊าซ (tCO2e/ปี):", 
                               help="ถ้าเป็นกองทุน ให้ใส่ค่าเฉลี่ยของบริษัทในพอร์ต", value=500000)
    
    # Physical Risk Context
    physical_risk_score = st.slider("ระดับความเสี่ยงทางกายภาพ (1-10):", 1, 10, 5, 
                                   help="1=ปลอดภัยมาก, 10=อยู่ในพื้นที่เสี่ยงภัยพิบัติสูง")
    
    wacc = st.slider("WACC / อัตราคิดลด (%)", 5.0, 15.0, 8.5) / 100

# --- 2. Data Processing & Calculations ---
@st.cache_data(ttl=3600)
def get_market_data(symbol):
    tickers = [symbol, BROWN_PROXY, GREEN_PROXY, SET_INDEX]
    data = yf.download(tickers, start="2022-01-01")['Close']
    returns = data.pct_change().dropna()
    current_price = data[symbol].iloc[-1]
    return returns, current_price

try:
    returns, last_price = get_market_data(ticker)
    
    # Calculate Carbon Beta (Transition Risk Sensitivity)
    bmg_factor = returns[BROWN_PROXY] - returns[GREEN_PROXY]
    Y = returns[ticker]
    X = pd.DataFrame({'Market': returns[SET_INDEX], 'Carbon_Factor': bmg_factor})
    X = sm.add_constant(X)
    model = sm.OLS(Y, X).fit()
    carbon_beta = model.params['Carbon_Factor']

    # --- 3. Financial Impact Calculation ---
    # A. Transition Impact (Carbon Tax Liability)
    annual_tax = emissions * CARBON_TAX_RATE
    valuation_impact = annual_tax / wacc # DCF Perpetuity
    impact_per_share = (valuation_impact / 1_000_000_000) # สมมติฐานเชิงสัดส่วน (Simplified)
    
    # B. Physical Impact (Physical VaR)
    # สมมติฐาน: ทุก 1 คะแนนความเสี่ยง มีโอกาสสูญเสียมูลค่า 1.5% ของสินทรัพย์ในระยะยาว
    physical_loss_pct = (physical_risk_score * 0.015) 
    physical_impact_total = (shares_owned * last_price) * physical_loss_pct
    
    # C. P&L Calculation
    current_value = shares_owned * last_price
    total_cost = shares_owned * avg_cost
    unrealized_pl = current_value - total_cost
    
    # Total Climate Impact (Combined)
    total_climate_loss = (annual_tax / 100) + physical_impact_total # ปรับสัดส่วนแสดงผล
    adjusted_value = current_value - total_climate_loss
    adjusted_pl = adjusted_value - total_cost

    # --- 4. Dashboard Display ---
    # Row 1: Market Status
    col1, col2, col3 = st.columns(3)
    col1.metric("ราคาปัจจุบัน (Last Price)", f"{last_price:,.2f} THB")
    col2.metric("มูลค่าพอร์ตปัจจุบัน", f"{current_value:,.2f} THB")
    col3.metric("กำไร/ขาดทุน (ปัจจุบัน)", f"{unrealized_pl:,.2f} THB", 
                delta=f"{(unrealized_pl/total_cost)*100:.2f}%")

    st.divider()

    # Row 2: Climate Risk Analysis
    st.subheader("🔍 Climate Risk Summary")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.write("**1. Transition Risk (คาร์บอน)**")
        st.info(f"Carbon Beta: {carbon_beta:.3f}")
        st.caption("ค่าบวก: เสี่ยงต่อภาษีคาร์บอน | ค่าลบ: ได้ประโยชน์จากการเปลี่ยนผ่าน")
    
    with c2:
        st.write("**2. Physical Risk (ภัยธรรมชาติ)**")
        st.warning(f"Score: {physical_risk_score}/10")
        st.caption("ผลกระทบจากน้ำท่วม/ภัยแล้ง ต่อทรัพย์สินของบริษัท")

    with c3:
        st.write("**3. Financial Summary (หลังหักความเสี่ยง)**")
        st.error(f"รวมความเสียหายคาดการณ์: -{total_climate_loss:,.2f} THB")

    # Row 3: Impact Analysis Table
    st.subheader("📊 Comparison Table: Normal vs Climate Scenario")
    summary_df = pd.DataFrame({
        "หัวข้อ": ["มูลค่าพอร์ต (THB)", "กำไร/ขาดทุน (THB)", "สถานะ"],
        "สถานการณ์ปกติ": [f"{current_value:,.2f}", f"{unrealized_pl:,.2f}", "Normal"],
        "หลังหักความเสี่ยง Climate": [f"{adjusted_value:,.2f}", f"{adjusted_pl:,.2f}", "Risky"]
    })
    st.table(summary_df)

    # Visualization
    fig = px.bar(x=["Normal Value", "Climate Adjusted Value"], 
                 y=[current_value, adjusted_value],
                 title="เปรียบเทียบมูลค่าพอร์ต (Current vs Adjusted)",
                 color=["Normal", "Climate Risk"],
                 labels={'x': '', 'y': 'Portfolio Value (THB)'})
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"ไม่สามารถดึงข้อมูลได้: {e}. กรุณาตรวจสอบว่าชื่อหุ้นลงท้ายด้วย .BK หรือยัง")
