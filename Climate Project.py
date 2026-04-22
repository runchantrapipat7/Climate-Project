import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.express as px

# 1. การตั้งค่าพื้นฐานและความเสี่ยงเชิงนโยบาย (Transition Risk)
# ประเทศไทยกำหนดภาษีคาร์บอนที่ 200 บาทต่อตัน (THB 200/tCO2e) เริ่มในปี 2025
CARBON_TAX_RATE = 200 
SET_INDEX = "^SET.BK"

st.set_page_config(page_title="Thai Climate Risk Analyzer", layout="wide")
st.title("🌍 Thai Stock Climate Risk Engine")
st.markdown("เครื่องมือวิเคราะห์ผลกระทบจากความเสี่ยงภูมิอากาศต่อราคาหุ้นและมูลค่ากิจการในตลาด SET")

# ส่วนอินพุตสำหรับวิเคราะห์รายบริษัท
with st.sidebar:
    st.header("Corporate Data")
    ticker = st.text_input("ระบุชื่อหุ้นไทย (เช่น PTT.BK, SCGP.BK):", "PTT.BK")
    emissions = st.number_input("ปริมาณการปล่อยก๊าซ Scope 1+2 (tCO2e/ปี):", value=1000000)
    wacc = st.slider("WACC หรือ อัตราคิดลด (%)", 5.0, 15.0, 8.5) / 100


# 2. ฟังก์ชันคำนวณ Carbon Beta เพื่อวัดความอ่อนไหวต่อ Transition Risk
def calculate_carbon_beta(stock_ticker):
    # กำหนดรายชื่อหุ้น: หุ้นที่เลือก + กลุ่ม Brown (PTTEP) + กลุ่ม Green (EA) + ดัชนี SET
    # เราใช้ PTTEP.BK และ EA.BK เป็นตัวแทน (Proxy) ของการเปลี่ยนผ่านพลังงานในไทย
    tickers =
    
    # ดึงข้อมูลย้อนหลังตั้งแต่ปี 2022 เพื่อหาความสัมพันธ์เชิงลึก
    data = yf.download(tickers, start="2022-01-01")['Close']
    returns = data.pct_change().dropna()
    
    # สร้าง BMG Factor (Brown-Minus-Green): 
    # คือส่วนต่างผลตอบแทนระหว่างหุ้น "น้ำตาล" (Brown) และหุ้น "เขียว" (Green) 
    # เพื่อวัด Climate Risk Premium ในตลาดหุ้นไทย
    bmg_factor = returns - returns
    
    # เตรียมข้อมูลสำหรับ Multi-factor Regression
    # Ri = alpha + beta_market * Rm + beta_carbon * BMG
    Y = returns[stock_ticker]
    X = pd.DataFrame({
        'Market': returns, 
        'Carbon_Factor': bmg_factor
    })
    X = sm.add_constant(X)
    
    model = sm.OLS(Y, X).fit()
    return model, returns

# 3. ส่วนการแสดงผลการวิเคราะห์
if st.button("Run Climate Risk Analysis"):
    with st.spinner('กำลังประมวลผลข้อมูล...'):
        model, returns_data = calculate_carbon_beta(ticker)
        
        # แสดงผล Carbon Beta: หากค่าเป็นบวกแสดงว่าหุ้นมีความเสี่ยงสูงต่อการเปลี่ยนผ่านสู่เศรษฐกิจต่ำ
        carbon_beta = model.params['Carbon_Factor']
        col1, col2 = st.columns(2)
        
        col1.metric("Market Beta", round(model.params['Market'], 2))
        col2.metric("Carbon Beta (Exposure)", round(carbon_beta, 3), 
                    delta="High Transition Risk" if carbon_beta > 0 else "Low Transition Risk",
                    delta_color="inverse")

        # 4. การจำลองผลกระทบต่อมูลค่า (Climate-Adjusted DCF)
        # คำนวณต้นทุนภาษีคาร์บอนและผลกระทบต่อมูลค่ากิจการตามหลัก Perpetuity Adjustment
        annual_tax_cost = emissions * CARBON_TAX_RATE
        valuation_impact = annual_tax_cost / wacc
        
        st.subheader("📊 Valuation Impact (Transition Risk)")
        st.write(f"หากไทยบังคับใช้ภาษีคาร์บอนที่ {CARBON_TAX_RATE} บาท/ตัน:")
        st.error(f"ต้นทุนภาษีคาร์บอนต่อปี: {annual_tax_cost:,.0f} บาท")
        st.warning(f"มูลค่ากิจการที่คาดว่าจะลดลง: -{valuation_impact:,.0f} บาท")

        # 5. ความเสี่ยงเชิงกายภาพ (Physical Risk Context)
        # ในไทย ความเสี่ยงหลักคืออุทกภัย (Floods) ซึ่งคิดเป็น 95% ของความเสียหายจากภัยธรรมชาติทั้งหมด
        st.subheader("🌊 Physical Risk Context: Flood Exposure")
        st.info("ลุ่มแม่น้ำเจ้าพระยา ซึ่งรวมถึงกรุงเทพฯ และปริมณฑล เป็นพื้นที่ที่มีความเสี่ยงสูงและสร้าง GDP ถึง 50% ของประเทศ")
        
        # กราฟเปรียบเทียบผลตอบแทนสะสม
        st.subheader("📈 Performance Visualization")
        fig = px.line(returns_data[ticker].cumsum(), title=f"Cumulative Returns of {ticker}")
        st.plotly_chart(fig, use_container_width=True)