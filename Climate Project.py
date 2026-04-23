import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Ultimate Climate Finance Intelligence", layout="wide")

# --- CSS: Professional Dashboard Theme ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px; border-radius: 15px;
    }
    [data-testid="stMetricValue"] > div { color: #2ECC71 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: rgba(255, 255, 255, 0.05); border-radius: 10px 10px 0 0; padding: 10px 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: MULTI-INPUT ---
with st.sidebar:
    st.title("⚖️ Portfolio Comparison")
    st.write("ระบุหุ้นที่ต้องการวิเคราะห์ (สูงสุด 3 ตัว)")
    t1 = st.text_input("หุ้นตัวที่ 1", "PTT.BK")
    t2 = st.text_input("หุ้นตัวที่ 2", "SCC.BK")
    t3 = st.text_input("หุ้นตัวที่ 3", "")
    
    tickers = [t.strip().upper() for t in [t1, t2, t3] if t.strip()]

    st.divider()
    st.header("🌍 Scenario & Policy (TCFD)")
    scenario = st.select_slider("Climate Ambition", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
    tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    st.divider()
    st.header("🌊 Physical Risk Control")
    flood_risk = st.slider("Flood Exposure (%)", 0, 100, 45)
    drought_risk = st.slider("Drought Exposure (%)", 0, 100, 30)
    wacc = st.slider("WACC (%)", 5.0, 15.0, 8.0) / 100

# --- CORE LOGIC: COMPREHENSIVE DATA ENGINE ---
@st.cache_data(ttl=3600)
def fetch_deep_analysis(ticker_list):
    try:
        all_to_fetch = ticker_list + ["PTTEP.BK", "EA.BK", "^SET.BK"]
        data = yf.download(all_to_fetch, start="2023-01-01", progress=False)['Close']
        returns = data.pct_change().dropna()
        
        full_results = {}
        for symbol in ticker_list:
            if symbol in returns.columns:
                t_obj = yf.Ticker(symbol)
                # 1. Modeling
                bmg = returns["PTTEP.BK"] - returns["EA.BK"]
                X = sm.add_constant(pd.DataFrame({'Market': returns["^SET.BK"], 'Carbon': bmg}))
                model = sm.OLS(returns[symbol], X).fit()
                
                # 2. Fundamentals & News
                try: info = t_obj.info
                except: info = {}
                try: news = t_obj.news[:5]
                except: news = []
                
                full_results[symbol] = {
                    "model": model,
                    "info": info,
                    "news": news,
                    "last_price": data[symbol].iloc[-1],
                    "history": data[symbol],
                    "carbon_beta": model.params['Carbon'],
                    "market_beta": model.params['Market']
                }
        return full_results, data[ticker_list]
    except: return None, None

# --- MAIN DASHBOARD ---
st.title("🏛️ Sustainable Finance & Climate Risk Intelligence")
st.markdown(f"**Comparative Market Terminal** | {datetime.now().strftime('%d %B %Y')}")

if tickers:
    analysis_data, price_history = fetch_deep_analysis(tickers)
    
    if analysis_data:
        # --- SECTION 1: OVERVIEW COMPARISON ---
        st.subheader("📊 Cross-Asset Comparison")
        comp_cols = st.columns(len(analysis_data))
        for i, (symbol, d) in enumerate(analysis_data.items()):
            with comp_cols[i]:
                st.metric(f"💎 {symbol}", f"{d['last_price']:.2f} THB", 
                          delta=f"Carbon Beta: {d['carbon_beta']:.3f}", delta_color="inverse")
        
        st.divider()

        # --- SECTION 2: INDIVIDUAL DEEP DIVE (TABS) ---
        st.subheader("🔍 Individual Deep Dive & Climate Analytics")
        tabs = st.tabs([f"Intelligence: {s}" for s in analysis_data.keys()])
        
        for i, (symbol, d) in enumerate(analysis_data.items()):
            with tabs[i]:
                # Row 1: Fundamentals
                st.markdown(f"### 🧬 {symbol}: Corporate Fundamentals")
                f1, f2, f3, f4 = st.columns(4)
                f1.metric("P/E Ratio", d['info'].get('trailingPE', 'N/A'))
                f2.metric("Div. Yield", f"{d['info'].get('dividendYield', 0)*100:.2f}%")
                f3.metric("Market Cap", f"{d['info'].get('marketCap', 0)/1e9:.1f}B")
                f4.metric("Market Beta", f"{d['market_beta']:.2f}")

                # Row 2: Charts (Price & Risk)
                c_left, c_right = st.columns([2, 1])
                with c_left:
                    st.subheader("📈 Price Momentum")
                    st.line_chart(d['history'])
                with c_right:
                    st.subheader("🔥 Carbon Sensitivity")
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number", value = d['carbon_beta'] * 100,
                        gauge = {'axis': {'range': [-50, 50]}, 'bar': {'color': "#E74C3C" if d['carbon_beta'] > 0 else "#2ECC71"}}))
                    fig_gauge.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_gauge, use_container_width=True)

                # Row 3: Climate Risk Modeling & Valuation
                st.divider()
                r_left, r_right = st.columns(2)
                with r_left:
                    st.subheader("🧬 Sustainable Finance Memo")
                    val_impact = (tax_price * 1000) / wacc / 1e6 # Simulation MB
                    st.info(f"""
                    **วิเคราะห์สำหรับ {symbol}:**
                    - **Transition Risk:** ความอ่อนไหว {d['carbon_beta']:.3f} สะท้อนความเสี่ยงต่อ {scenario}
                    - **Valuation Discount:** คาดการณ์ผลกระทบภาษีคาร์บอนทำให้มูลค่าหายไป **-{val_impact:,.2f} ล้านบาท**
                    - **Physical Exposure:** {flood_risk}% Flood Risk (ลุ่มแม่น้ำเจ้าพระยา)
                    """)
                    
                    # Waterfall
                    fig_water = go.Figure(go.Waterfall(
                        x = ["Market Cap", "Climate Loss", "Adjusted Value"],
                        y = [d['info'].get('marketCap', 1e9)/1e6, -val_impact, (d['info'].get('marketCap', 1e9)/1e6) - val_impact],
                        measure = ["relative", "relative", "total"]
                    ))
                    fig_water.update_layout(height=300)
                    st.plotly_chart(fig_water, use_container_width=True)

                with r_right:
                    st.subheader("📰 Market Intelligence & News")
                    if d['news']:
                        for n in d['news']:
                            st.write(f"**[{n.get('publisher','N/A')}]** - {n.get('title','N/A')}")
                            st.write(f"[อ่านต่อ]({n.get('link','#')})")
                            st.divider()
                    else: st.warning("ไม่มีข้อมูลข่าวสารล่าสุด")

        # --- SECTION 3: PERFORMANCE COMPARISON CHART ---
        st.divider()
        st.subheader("📉 Relative Performance Comparison")
        norm_prices = (price_history / price_history.iloc[0]) * 100
        fig_comp = px.line(norm_prices, title="Normalized Performance (Base 100)")
        st.plotly_chart(fig_comp, use_container_width=True)
        
    else:
        st.error("❌ ไม่พบข้อมูลสำหรับ Ticker ที่ระบุ กรุณาตรวจสอบชื่อหุ้น (เช่น PTT.BK)")
