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
    
    # --- คืนหัวข้อที่คุณต้องการตรงนี้ครับ ---
    st.header("🔍 ระบุชื่อหุ้นหรือกองทุน (Stock or Bond)")
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

# --- DATA ENGINE (FIXED STABILITY) ---
@st.cache_data(ttl=300)
def fetch_robust_data(ticker_list):
    full_res = {}
    history_map = {}
    
    # ดึงข้อมูล Proxy เพื่อใช้คำนวณ Carbon Beta จริงๆ
    try:
        proxies = yf.download(["PTTEP.BK", "EA.BK", "^SET.BK"], period="2y", progress=False)['Close']
        proxies = proxies.ffill().bfill()
    except:
        proxies = pd.DataFrame()

    for symbol in ticker_list:
        try:
            t_obj = yf.Ticker(symbol)
            hist = t_obj.history(period="2y")['Close']
            
            if hist.empty: continue
            
            history_map[symbol] = hist
            
            # คำนวณ Carbon Beta จริงๆ
            c_beta, m_beta = 0.0, 1.0
            if not proxies.empty:
                try:
                    temp_df = pd.concat([hist, proxies], axis=1).pct_change().dropna()
                    bmg = temp_df["PTTEP.BK"] - temp_df["EA.BK"]
                    X = sm.add_constant(pd.DataFrame({'Market': temp_df["^SET.BK"], 'Carbon': bmg}))
                    model = sm.OLS(temp_df[symbol], X).fit()
                    c_beta, m_beta = model.params.get('Carbon', 0.0), model.params.get('Market', 1.0)
                except: pass

            full_res[symbol] = {
                "last_price": hist.iloc[-1],
                "history": hist,
                "carbon_beta": c_beta,
                "market_beta": m_beta,
                "info": t_obj.info if t_obj.info else {},
                "news": t_obj.news[:5] if t_obj.news else []
            }
            time.sleep(0.2)
        except: continue
            
    return full_res, pd.DataFrame(history_map)

# --- MAIN DISPLAY ---
st.title("🏛️ Sustainable Finance & Climate Risk Modeling")
st.markdown(f"Market Intelligence Terminal | {datetime.now().strftime('%d %Y')}")

if tickers:
    with st.spinner('กำลังเชื่อมต่อฐานข้อมูล...'):
        analysis, history = fetch_robust_data(tickers)
    
    if analysis:
        # Overview Metrics
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
                
                # ป้องกัน Error กรณีไม่มีข้อมูลพื้นฐาน
                m_cap = d['info'].get('marketCap')
                f3.metric("Div. Yield", f"{d['info'].get('dividendYield', 0)*100:.2f}%" if d['info'].get('dividendYield') else "N/A")
                f4.metric("Market Cap", f"{m_cap/1e9:.1f}B" if m_cap else "N/A")

                # Charts
                c_l, c_r = st.columns([2, 1])
                with c_l:
                    st.subheader("📈 Price Momentum")
                    st.line_chart(d['history'])
                with c_r:
                    st.subheader("🔥 Carbon Sensitivity")
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number", value = d['carbon_beta'] * 100,
                        gauge = {'axis': {'range': [-50, 50]}, 'bar': {'color': "#2ECC71" if d['carbon_beta'] < 0 else "#E74C3C"}}))
                    fig_gauge.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig_gauge, use_container_width=True)

                # Waterfall Chart (แก้ Error ValueError ที่นี่)
                st.divider()
                st.subheader("💰 Equity Value Bridge (MB)")
                mkt_cap_mb = float(m_cap)/1e6 if m_cap else 1000.0
                val_impact = (tax_price * 1000) / wacc / 1e6
                
                # FIXED: เพิ่มพารามิเตอร์ 'y' ให้ครบถ้วน
                fig_water = go.Figure(go.Waterfall(
                    orientation = "v",
                    x = ["Current Cap", "Climate Loss", "Adjusted Value"],
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
                        st.write(f"[อ่านต่อ]({n.get('link','#')})")
                        st.divider()
    else:
        st.error("❌ ไม่พบข้อมูลสำหรับรายชื่อที่ระบุ กรุณารอ 10 วินาทีแล้วลอง Refresh หรือใช้ Ticker อื่น (เช่น PTT.BK, EA.BK)")
