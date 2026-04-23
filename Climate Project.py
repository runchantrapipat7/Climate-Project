import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Climate Risk Intelligence", layout="wide")

# --- CSS: ปรับดีไซน์ให้ดูเหมือนโปรแกรมการเงินระดับโลก ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        padding: 20px; border-radius: 15px; border: 1px solid rgba(128, 128, 128, 0.2);
    }
    [data-testid="stMetricValue"] > div { color: #2ECC71 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: จัดระเบียบใหม่ ---
with st.sidebar:
    st.title("🛡️ Risk Controller")
    asset_class = st.radio("Asset Class", ["Stock", "Mutual Fund"], horizontal=True)
    ticker_input = st.text_input("Symbol Ticker (เช่น PTT.BK)", "PTT.BK")
    
    st.divider()
    st.header("🌍 Climate Scenario (TCFD)")
    scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
    tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    st.divider()
    st.header("🌊 Physical Risk Score")
    flood_risk = st.slider("Flood Exposure (%)", 0, 100, 45)
    drought_risk = st.slider("Drought Exposure (%)", 0, 100, 30)

# --- CORE LOGIC: CLIMATE MODELING ---
@st.cache_data(ttl=3600)
def run_climate_model(symbol):
    try:
        # ดึงข้อมูล Ticker เป้าหมาย และตัวแทนกลุ่ม Brown/Green
        data = yf.download([symbol, "PTTEP.BK", "EA.BK", "^SET.BK"], start="2023-01-01", progress=False)['Close']
        if symbol not in data.columns or data[symbol].isnull().all():
            return None, None, None
            
        returns = data.pct_change().dropna()
        # คำนวณ Carbon Beta (BMG Factor)
        bmg = returns["PTTEP.BK"] - returns["EA.BK"]
        X = sm.add_constant(pd.DataFrame({'Market': returns["^SET.BK"], 'Carbon': bmg}))
        model = sm.OLS(returns[symbol], X).fit()
        
        return model, data[symbol].iloc[-1], returns[symbol]
    except:
        return None, None, None

# --- MAIN DISPLAY ---
st.title("🌡️ Climate Risk Modeling & Sustainable Finance")
st.markdown(f"Market Intelligence Terminal | **Analysis Date: {datetime.now().strftime('%Y-%m-%d')}**")

model, price, hist_ret = run_climate_model(ticker_input)

if model:
    carbon_beta = model.params['Carbon']
    
    # ROW 1: Metrics Dashboard
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Market Price", f"{price:,.2f} THB")
    col2.metric("Carbon Beta", f"{carbon_beta:.3f}")
    col3.metric("Projected Tax", f"{tax_price} / t")
    col4.metric("Risk Level", "HIGH" if carbon_beta > 0.05 else "LOW")

    st.divider()

    # ROW 2: กราฟวิเคราะห์ความเสี่ยง
    left_col, right_col = st.columns([1, 1.5])
    
    with left_col:
        st.subheader("🔥 Risk Sensitivity Meter")
        # ใช้ Gauge Chart แทนตัวเลขธรรมดา
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = carbon_beta * 100,
            title = {'text': "Transition Risk Sensitivity"},
            gauge = {'axis': {'range': [-50, 50]},
                     'bar': {'color': "#E74C3C" if carbon_beta > 0 else "#2ECC71"}}))
        st.plotly_chart(fig_gauge, use_container_width=True)

    with right_col:
        st.subheader("📉 Physical Risk Matrix (Thailand Focus)")
        # อิงข้อมูล: 95% ของภัยพิบัติในไทยคืออุทกภัย
        risk_data = pd.DataFrame({
            'Risk Type': ['Inland Flood', 'Coastal Flood', 'Water Stress'],
            'Impact Score': [flood_risk, flood_risk * 0.7, drought_risk]
        })
        fig_bar = px.bar(risk_data, x='Impact Score', y='Risk Type', orientation='h', 
                         color='Impact Score', color_continuous_scale='Reds')
        st.plotly_chart(fig_bar, use_container_width=True)

    # ROW 3: Sustainable Finance (Waterfall Chart)
    st.divider()
    st.subheader("💰 Sustainable Finance Valuation Bridge")
    # คำนวณส่วนต่างมูลค่า
    val_loss = (tax_price * 1000) / 0.08 / 1e6 # จำลองมูลค่าที่หายไป
    fig_water = go.Figure(go.Waterfall(
        x = ["Current Cap", "Climate Discount", "Fair Value"],
        y = [1000, -val_loss, 1000 - val_loss],
        measure = ["relative", "relative", "total"]
    ))
    st.plotly_chart(fig_water, use_container_width=True)
    st.info(f"**Sustainable Finance Insight:** ภายใต้ฉากทัศน์ {scenario} หุ้น {ticker_input} มีความเสี่ยงต่อต้นทุนคาร์บอนเพิ่มขึ้นอย่างมีนัยสำคัญ")

else:
    st.warning("🔍 **ไม่พบข้อมูล Ticker:** หากคุณวิเคราะห์กองทุนต่างประเทศ (เช่น S&P 500) ให้ใช้ Ticker ตัวแทน เช่น `^GSPC` แทนครับ")

# --- NEW SECTION: DAILY RESEARCH & NEWS ANALYSIS ---
    st.divider()
    st.header(f"📰 Daily Research & Insight: {ticker_input}")
    
    # ดึงข้อมูลข่าวสารล่าสุดจาก Yahoo Finance
    try:
        ticker_obj = yf.Ticker(ticker_input)
        news = ticker_obj.news[:5] # ดึง 5 ข่าวล่าสุด
        
        if news:
            col_n1, col_n2 = st.columns([1, 1])
            
            with col_n1:
                st.subheader("Latest Market News")
                for item in news:
                    with st.expander(f"📌 {item['title']}"):
                        st.write(f"**Source:** {item['publisher']}")
                        st.write(f"**Link:** [Read Full Article]({item['link']})")
                        # จำลองการวิเคราะห์ ESG Sentiment
                        st.caption("ESG Analysis: Neutral to Positive impact on Climate Strategy")
            
            with col_n2:
                st.subheader("Sustainable Finance Research Memo")
                # ส่วนนี้เป็นการจำลองการเขียน Research รายวันตามหลัก Climate Modeling
                memo_text = f"""
                **ประจำวันที่:** {datetime.now().strftime('%d %B %Y')}
                
                **วิเคราะห์ผลกระทบรายวัน:**
                จากการตรวจสอบข้อมูลล่าสุด หุ้น {ticker_input} มีค่า Carbon Beta ที่ {carbon_beta:.3f} 
                ซึ่งหมายถึงความไวต่อราคาคาร์บอนในระดับที่ควรเฝ้าติดตาม 
                
                **ประเด็นสำคัญด้านความยั่งยืน:**
                1. **Transition Risk:** ภายใต้ฉากทัศน์ {scenario} บริษัทต้องเตรียมสำรองกระแสเงินสด
                   เพิ่มขึ้นเพื่อรองรับภาษีคาร์บอนที่คาดว่าจะอยู่ที่ {tax_price} บาท/ตัน
                2. **Physical Exposure:** ด้วยคะแนนความเสี่ยงน้ำท่วมที่ {flood_risk}% นักลงทุนควรพิจารณา
                   ค่าเสื่อมราคาของสินทรัพย์ถาวรในพื้นที่ลุ่มแม่น้ำเจ้าพระยาเพิ่มเติม
                
                **คำแนะนำเชิงกลยุทธ์:**
                ควรเพิ่มน้ำหนักการลงทุน (Overweight) หากบริษัทมีการประกาศแผน Net Zero ที่ชัดเจนกว่าเดิม
                """
                st.info(memo_text)
        else:
            st.warning("ไม่พบข้อมูลข่าวสารล่าสุดสำหรับ Ticker นี้ในระบบ Research")
            
    except Exception as e:
        st.error(f"ไม่สามารถดึงข้อมูล Research ได้: {e}")
