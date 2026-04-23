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
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: rgba(255, 255, 255, 0.05); border-radius: 10px 10px 0 0; padding: 10px 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: MULTI-INPUT ---
with st.sidebar:
    st.title("⚖️ Portfolio Comparison")
    st.write("ระบุ Ticker หุ้นหรือกองทุน (สูงสุด 3 ตัว)")
    t1 = st.text_input("Asset 1", "PTT.BK")
    t2 = st.text_input("Asset 2", "^GSPC") # ตัวอย่าง S&P 500
    t3 = st.text_input("Asset 3", "")
    
    tickers = [t.strip().upper() for t in [t1, t2, t3] if t.strip()]

    st.divider()
    st.header("🌍 Scenario & Policy (TCFD)")
    scenario = st.select_slider("Climate Ambition", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
    tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    st.divider()
    st.header("🌊 Physical Risk Control")
    flood_risk = st.slider("Flood Exposure (%)", 0, 100, 45)
    wacc = st.slider("WACC (%)", 5.0, 15.0, 8.0) / 100

# --- CORE LOGIC: DATA ENGINE (Fixed for Mutual Funds) ---
@st.cache_data(ttl=3600)
def fetch_comprehensive_data(ticker_list):
    try:
        # พยายามดึงข้อมูลหลัก
        data = yf.download(ticker_list, start="2023-01-01", progress=False)['Close']
        if isinstance(data, pd.Series): data = data.to_frame()
        
        # ดึง Proxy เฉพาะสำหรับคำนวณ Carbon Beta (ถ้าทำได้)
        proxies = yf.download(["PTTEP.BK", "EA.BK", "^SET.BK"], start="2023-01-01", progress=False)['Close']
        
        full_results = {}
        for symbol in ticker_list:
            if symbol in data.columns:
                t_obj = yf.Ticker(symbol)
                
                # Default values
                c_beta = 0.0
                m_beta = 1.0
                
                # คำนวณ Modeling (ถ้าข้อมูล Proxy ครบ)
                try:
                    combined = pd.concat([data[symbol], proxies], axis=1).pct_change().dropna()
                    bmg = combined["PTTEP.BK"] - combined["EA.BK"]
                    X = sm.add_constant(pd.DataFrame({'Market': combined["^SET.BK"], 'Carbon': bmg}))
                    model = sm.OLS(combined[symbol], X).fit()
                    c_beta = model.params['Carbon']
                    m_beta = model.params['Market']
                except: pass # ถ้าเป็นกองทุนต่างประเทศจะข้ามการคำนวณส่วนนี้ไปเพื่อให้แอปไม่พัง
                
                try: info = t_obj.info
                except: info = {}
                try: news = t_obj.news[:5]
                except: news = []
                
                full_results[symbol] = {
                    "info": info, "news": news,
                    "last_price": data[symbol].dropna().iloc[-1] if not data[symbol].dropna().empty else 0,
                    "history": data[symbol],
                    "carbon_beta": c_beta,
                    "market_beta": m_beta
                }
        return full_results, data
    except Exception as e:
        return None, None

# --- MAIN DISPLAY ---
st.title("🏛️ Sustainable Finance & Climate Risk Intelligence")
st.markdown(f"**Comparative Market Terminal** | {datetime.now().strftime('%d %B %Y')}")

if tickers:
    analysis_data, price_history = fetch_comprehensive_data(tickers)
    
    if analysis_data:
        # --- SECTION 1: OVERVIEW ---
        comp_cols = st.columns(len(analysis_data))
        for i, (symbol, d) in enumerate(analysis_data.items()):
            with comp_cols[i]:
                st.metric(f"💎 {symbol}", f"{d['last_price']:,.2f}", delta=f"C-Beta: {d['carbon_beta']:.3f}")

        # --- SECTION 2: TABS ---
        tabs = st.tabs([f"Asset: {s}" for s in analysis_data.keys()])
        for i, (symbol, d) in enumerate(analysis_data.items()):
            with tabs[i]:
                st.markdown(f"#### 🧬 {symbol} Analysis")
                f1, f2, f3, f4 = st.columns(4)
                f1.metric("Current Price", f"{d['last_price']:,.2f}")
                f2.metric("Market Beta", f"{d['market_beta']:.2f}")
                f3.metric("Div. Yield", f"{d['info'].get('dividendYield', 0)*100:.2f}%")
                f4.metric("Market Cap", f"{d['info'].get('marketCap', 0)/1e9:.1f}B")

                c_left, c_right = st.columns([2, 1])
                with c_left:
                    st.subheader("📈 Price Momentum")
                    st.line_chart(d['history'])
                with c_right:
                    st.subheader("🔥 Carbon Sensitivity")
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number", value = d['carbon_beta'] * 100,
                        gauge = {'axis': {'range': [-50, 50]}, 'bar': {'color': "#E74C3C" if d['carbon_beta'] > 0 else "#2ECC71"}}))
                    st.plotly_chart(fig_gauge, use_container_width=True)

                st.divider()
                r_left, r_right = st.columns(2)
                with r_left:
                    val_impact = (tax_price * 1000) / wacc / 1e6
                    st.info(f"**Climate Insight:** {symbol} เสี่ยงอุทกภัย {flood_risk}% ผลกระทบมูลค่าคาร์บอน -{val_impact:,.2f}M")
                    # Waterfall
                    fig_water = go.Figure(go.Waterfall(
                        x = ["Market Cap", "Climate Loss", "Adjusted"],
                        y = [d['info'].get('marketCap', 1e9)/1e6, -val_impact, (d['info'].get('marketCap', 1e9)/1e6) - val_impact],
                        measure = ["relative", "relative", "total"]))
                    st.plotly_chart(fig_water, use_container_width=True)
                with r_right:
                    st.subheader("📰 Latest News")
                    for n in d['news']:
                        st.write(f"**[{n.get('publisher','N/A')}]** {n.get('title','N/A')}")
                        st.write(f"[อ่านต่อ]({n.get('link','#')})")
                        st.divider()
    else:
        st.error("ไม่พบข้อมูล Ticker")
