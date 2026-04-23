import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Climate Finance Terminal", layout="wide")

# --- CSS: High-Contrast Dashboard ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px; border-radius: 15px;
    }
    [data-testid="stMetricValue"] > div { color: #2ECC71 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: MULTI-INPUT ---
with st.sidebar:
    st.title("⚖️ Portfolio Intelligence")
    t1 = st.text_input("Asset 1", "PTT.BK")
    t2 = st.text_input("Asset 2", "EA.BK")
    t3 = st.text_input("Asset 3", "")
    tickers = [t.strip().upper() for t in [t1, t2, t3] if t.strip()]

    st.divider()
    st.header("🌍 Climate Scenario (TCFD)")
    scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
    tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    st.divider()
    st.header("🌊 Physical Risk Control")
    flood_risk = st.slider("Flood Exposure (%)", 0, 100, 45)
    wacc = st.slider("WACC (%)", 5.0, 15.0, 8.0) / 100

# --- CORE LOGIC: REFINED DATA ENGINE ---
@st.cache_data(ttl=3600)
def fetch_analysis_data(ticker_list):
    try:
        # ดึงข้อมูลย้อนหลัง 5 ปีเพื่อให้เห็น Momentum ชัดเจน
        all_fetch = ticker_list + ["PTTEP.BK", "EA.BK", "^SET.BK"]
        data = yf.download(all_fetch, period="5y", interval="1d", progress=False)['Close']
        
        # จัดการข้อมูลกรณีมีหุ้นตัวเดียว
        if isinstance(data, pd.Series): data = data.to_frame()
        data = data.dropna(how='all') # ลบวันที่ไม่มีข้อมูลออกทั้งหมด

        full_res = {}
        for symbol in ticker_list:
            if symbol in data.columns:
                stock_data = data[symbol].dropna()
                if stock_data.empty: continue
                
                # Modeling (Transition Risk)
                try:
                    mkt_data = data[["PTTEP.BK", "EA.BK", "^SET.BK"]].dropna()
                    combined = pd.concat([stock_data, mkt_data], axis=1).pct_change().dropna()
                    bmg = combined["PTTEP.BK"] - combined["EA.BK"]
                    X = sm.add_constant(pd.DataFrame({'Market': combined["^SET.BK"], 'Carbon': bmg}))
                    model = sm.OLS(combined[symbol], X).fit()
                    c_beta, m_beta = model.params['Carbon'], model.params['Market']
                except: c_beta, m_beta = 0.0, 1.0

                t_obj = yf.Ticker(symbol)
                full_res[symbol] = {
                    "last_price": stock_data.iloc[-1],
                    "history": stock_data,
                    "carbon_beta": c_beta,
                    "market_beta": m_beta,
                    "info": t_obj.info,
                    "news": t_obj.news[:5]
                }
        return full_res, data[ticker_list].dropna()
    except: return None, None

# --- MAIN DASHBOARD ---
st.title("🏛️ Sustainable Finance & Climate Risk Modeling")
st.markdown(f"**Comparative Terminal** | {datetime.now().strftime('%d %B %Y')}")

if tickers:
    analysis, history = fetch_analysis_data(tickers)
    
    if analysis:
        # 1. Overview Comparison Cards
        cols = st.columns(len(analysis))
        for i, (symbol, d) in enumerate(analysis.items()):
            with cols[i]:
                st.metric(f"💎 {symbol}", f"{d['last_price']:,.2f}", delta=f"C-Beta: {d['carbon_beta']:.3f}")

        # 2. Tabs for Deep Dive
        tabs = st.tabs([f"Intelligence: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                # ROW 1: Price Momentum (จุดที่แก้ไข)
                st.subheader(f"📈 {symbol} Price Momentum (5-Year History)")
                fig_mom = px.line(d['history'], labels={'value': 'Price (THB)', 'Date': ''})
                fig_mom.update_traces(line_color='#2ECC71')
                fig_mom.update_layout(xaxis_rangeslider_visible=False, height=400)
                st.plotly_chart(fig_mom, use_container_width=True)

                # ROW 2: Fundamentals & Sensitivity
                st.divider()
                c_l, c_r = st.columns([1.5, 1])
                with c_l:
                    st.markdown("#### 🧬 Sustainable Finance Analytics")
                    f1, f2, f3 = st.columns(3)
                    f1.metric("Market Beta", f"{d['market_beta']:.2f}")
                    f2.metric("Div. Yield", f"{d['info'].get('dividendYield', 0)*100:.2f}%")
                    f3.metric("Market Cap", f"{d['info'].get('marketCap', 0)/1e9:.1f}B")
                    
                    val_impact = (tax_price * 1000) / wacc / 1e6
                    st.info(f"**Climate Insight:** {symbol} เสี่ยงอุทกภัย {flood_risk}% | Impact: -{val_impact:,.2f}M")
                    # Waterfall
                    fig_water = go.Figure(go.Waterfall(
                        x = ["Market Cap", "Climate Loss", "Adjusted"],
                        y = [d['info'].get('marketCap', 1e9)/1e6, -val_impact, (d['info'].get('marketCap', 1e9)/1e6) - val_impact],
                        measure = ["relative", "relative", "total"]))
                    st.plotly_chart(fig_water, use_container_width=True)

                with c_r:
                    st.markdown("#### 🔥 Carbon Sensitivity")
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number", value = d['carbon_beta'] * 100,
                        gauge = {'axis': {'range': [-50, 50]}, 'bar': {'color': "#E74C3C" if d['carbon_beta'] > 0 else "#2ECC71"}}))
                    st.plotly_chart(fig_gauge, use_container_width=True)
                    
                    st.subheader("📰 Latest Insights")
                    for n in d['news']:
                        st.write(f"**[{n.get('publisher','N/A')}]** {n.get('title','N/A')}")
                        st.divider()

        # 3. Comparative Momentum
        st.divider()
        st.subheader("📉 Multi-Asset Relative Performance (Normalized)")
        norm_prices = (history / history.iloc[0]) * 100
        st.line_chart(norm_prices)

    else: st.error("ไม่พบข้อมูลสำหรับ Ticker ที่ระบุ")
