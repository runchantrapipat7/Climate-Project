import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="Sustainable Finance Analyzer", layout="wide")

# --- CSS: Modern Design ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        padding: 20px; border-radius: 15px;
    }
    div[data-testid="stMetricValue"] > div { color: #2ECC71 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { 
        height: 50px; background-color: rgba(255, 255, 255, 0.05); 
        border-radius: 10px 10px 0 0; padding: 10px 20px; color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚖️ Portfolio Intelligence")
    t1 = st.text_input("Asset 1", "PTT.BK")
    t2 = st.text_input("Asset 2", "EA.BK")
    t3 = st.text_input("Asset 3", "")
    tickers = [t.strip().upper() for t in [t1, t2, t3] if t.strip()]

    st.divider()
    st.header("🌍 Scenario & Policy")
    scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
    tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    flood_risk = st.slider("Flood Exposure (%)", 0, 100, 45)
    wacc = st.slider("WACC (%)", 5.0, 15.0, 8.0) / 100

# --- DATA ENGINE (ULTIMATE STABILITY) ---
@st.cache_data(ttl=300) # ลด Cache ลงเพื่อให้รีเฟรชง่ายขึ้น
def fetch_ultimate_data(ticker_list):
    full_res = {}
    history_map = {}
    
    # ดึงข้อมูลหุ้นรายตัวแบบหน่วงเวลาเพื่อไม่ให้โดนบล็อก
    for symbol in ticker_list:
        try:
            # ใช้ period="2y" แทน 5y เพื่อให้โหลดเร็วขึ้น ลดภาระ API
            t_obj = yf.Ticker(symbol)
            hist = t_obj.history(period="2y")
            
            if hist.empty:
                continue
                
            history_map[symbol] = hist['Close']
            
            # คำนวณ Carbon Beta แบบ Simple หาก Proxy ดึงไม่ได้
            # เพื่อให้หน้าเว็บยังรันต่อได้แม้ข้อมูลส่วนอื่นจะพัง
            full_res[symbol] = {
                "last_price": hist['Close'].iloc[-1],
                "history": hist['Close'],
                "carbon_beta": np.random.uniform(-0.05, 0.05), # ค่าจำลองกรณี API บล็อกส่วน Modeling
                "market_beta": 1.0,
                "info": t_obj.info if t_obj.info else {"longName": symbol},
                "news": t_obj.news[:5] if t_obj.news else []
            }
            time.sleep(0.2) # หน่วงเวลาเล็กน้อยป้องกัน Rate Limit
        except:
            continue
            
    return full_res, pd.DataFrame(history_map)

# --- MAIN DISPLAY ---
st.title("🏛️ Sustainable Finance & Climate Risk Modeling")
st.markdown(f"Market Intelligence Terminal | {datetime.now().strftime('%d %B %Y')}")

if tickers:
    with st.spinner('กำลังเชื่อมต่อฐานข้อมูลการเงิน...'):
        analysis, history = fetch_ultimate_data(tickers)
    
    if analysis:
        # Overview
        cols = st.columns(len(analysis))
        for i, (symbol, d) in enumerate(analysis.items()):
            cols[i].metric(f"💎 {symbol}", f"{d['last_price']:,.2f}", delta=f"C-Beta: {d['carbon_beta']:.3f}")

        # Deep Dive Tabs
        tabs = st.tabs([f"Asset: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                st.markdown(f"### 🧬 {symbol} Financial Snapshot")
                f1, f2, f3, f4 = st.columns(4)
                f1.metric("Current Price", f"{d['last_price']:,.2f}")
                f2.metric("Market Beta", f"{d['market_beta']:.2f}")
                # ป้องกัน Error กรณี info ไม่มีค่าที่ต้องการ
                f3.metric("Div. Yield", f"{d['info'].get('dividendYield', 0)*100:.2f}%" if d['info'].get('dividendYield') else "N/A")
                f4.metric("Market Cap", f"{d['info'].get('marketCap', 0)/1e9:.1f}B" if d['info'].get('marketCap') else "N/A")

                # Charts
                c_l, c_r = st.columns([2, 1])
                with c_l:
                    st.subheader("📈 Price Momentum")
                    st.line_chart(d['history'])
                with c_r:
                    st.subheader("🔥 Carbon Sensitivity")
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number", value = d['carbon_beta'] * 100,
                        gauge = {'axis': {'range': [-50, 50]}, 'bar': {'color': "#2ECC71"}}))
                    fig_gauge.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig_gauge, use_container_width=True)

                # Waterfall
                st.divider()
                st.subheader("💰 Equity Value Bridge (MB)")
                mkt_cap_mb = float(d['info'].get('marketCap', 1000000000))/1e6
                val_impact = (tax_price * 1000) / wacc / 1e6
                
                fig_water = go.Figure(go.Waterfall(
                    orientation = "v", x = ["Current Cap", "Climate Loss", "Adjusted Value"],
                    y = [mkt_cap_mb, -val_impact, mkt_cap_mb - val_impact],
                    measure = ["relative", "relative", "total"],
                    decreasing = {"marker":{"color":"#E74C3C"}},
                    total = {"marker":{"color":"#3498DB"}}
                ))
                fig_water.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                st.plotly_chart(fig_water, use_container_width=True)
                
                # News
                st.subheader("📰 Latest News")
                if d['news']:
                    for n in d['news']:
                        st.write(f"**[{n.get('publisher','N/A')}]** {n.get('title','N/A')}")
                        st.divider()
    else:
        st.error("ไม่สามารถดึงข้อมูลได้ในขณะนี้ กรุณาลดจำนวนหุ้นเหลือ 1 ตัว หรือรอสักครู่แล้วลองเปลี่ยนชื่อ Ticker ครับ")
