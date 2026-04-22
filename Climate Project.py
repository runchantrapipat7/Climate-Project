import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.express as px

# 1. การตั้งค่าพื้นฐาน
CARBON_TAX_RATE = 200 
SET_INDEX = "^SET.BK"

st.set_page_config(page_title="Thai Climate Risk Analyzer", layout="wide")
st.title("🌍 Thai Stock Climate Risk Engine")

# ส่วนอินพุต
with st.sidebar:
    st.header("Corporate Data")
    ticker = st.text_input("ระบุชื่อหุ้นไทย (เช่น PTT.BK, SCGP.BK):", "PTT.BK")
    emissions = st.number_input("ปริมาณการปล่อยก๊าซ Scope 1+2 (tCO2e/ปี):", value=1000000)
    wacc = st.slider("WACC หรือ อัตราคิดลด (%)", 5.0, 15.0, 8.5) / 100

# 2. ฟังก์ชันคำนวณที่แก้ไขแล้ว
def calculate_carbon_beta(stock_ticker):
    # กำหนดรายชื่อหุ้นให้ครบถ้วน
    tickers_list = [stock_ticker, "PTTEP.BK", "EA.BK", SET_INDEX]
    
    # ดึงข้อมูล
    data = yf.download(tickers_list, start="2022-01-01")['Close']
    returns = data.pct_change().dropna()
    
    # สร้าง BMG Factor (Brown-Minus-Green)
    bmg_factor = returns['PTTEP.BK'] - returns['EA.BK']
    
    # เตรียมข้อมูลสำหรับ Regression
    Y = returns[stock_ticker]
    X = pd.DataFrame({
        'Market': returns[SET_INDEX], 
        'Carbon_Factor': bmg_factor
    })
    X = sm.add_constant(X)
    
    model = sm.OLS(Y, X).fit()
    return model, returns

# 3. ส่วนการแสดงผล
if st.button("Run Climate Risk Analysis"):
    try:
        with st.spinner('กำลังประมวลผลข้อมูล...'):
            model, returns_data = calculate_carbon_beta(ticker)
            
            carbon_beta = model.params['Carbon_Factor']
            col1, col2 = st.columns(2)
            
            col1.metric("Market Beta", round(model.params['Market'], 2))
            col2.metric("Carbon Beta (Exposure)", round(carbon_beta, 3), 
                        delta="High Transition Risk" if carbon_beta > 0 else "Low Transition Risk",
                        delta_color="inverse")

            # การคำนวณผลกระทบต่อมูลค่า
            annual_tax_cost = emissions * CARBON_TAX_RATE
            valuation_impact = annual_tax_cost / wacc
            
            st.subheader("📊 Valuation Impact")
            st.error(f"ต้นทุนภาษีคาร์บอนต่อปี: {annual_tax_cost:,.0f} บาท")
            st.warning(f"มูลค่ากิจการที่คาดว่าจะลดลง (DCF): -{valuation_impact:,.0f} บาท")

            # กราฟ
            fig = px.line(returns_data[ticker].cumsum(), title=f"Cumulative Returns of {ticker}")
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e} (ตรวจสอบว่าชื่อหุ้นถูกต้องและมี .BK ต่อท้าย)")
