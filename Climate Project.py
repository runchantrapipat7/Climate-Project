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

# --- CSS: Modern Glassmorphism & High-Contrast Theme ---
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
    .stInfo { border-radius: 15px; background-color: rgba(46, 204, 113, 0.1); border: none; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: ASSET & RISK CONTROL ---
with st.sidebar:
    st.title("⚖️ Portfolio Intelligence")
    st.write("ระบุหุ้นหรือกองทุน (สูงสุด 3 ตัว)")
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
    drought_risk = st.slider("Drought Exposure (%)", 0, 100, 30)
    wacc = st.slider("WACC (%)", 5.0, 15.0, 8.0) / 100

# --- CORE LOGIC: DATA ENGINE ---
@st.cache_data(ttl=3600)
def fetch_analysis_data(ticker_list):
    try:
        # ดึงข้อมูลย้อนหลัง 5 ปีเพื่อให้ Momentum ชัดเจน
        all_fetch = ticker_list + ["PTTEP.BK", "EA.BK", "^SET.BK"]
        data = yf.download(all_fetch, period="5y", interval="1d", progress=False)['Close']
        if isinstance(data, pd.Series): data = data.to_frame()
        data = data.dropna(how='all')

        full_res = {}
        for symbol in ticker_list:
            if symbol in data.columns:
                stock_history = data[symbol].dropna()
                if stock_history.empty: continue
                
                # Modeling Transition Risk (Carbon Beta)
                try:
                    mkt_data = data[["PTTEP.BK", "EA.BK", "^SET.BK"]].dropna()
                    combined = pd.concat([stock_history, mkt_data], axis=1).pct_change().dropna()
                    bmg = combined["PTTEP.BK"] - combined["EA.BK"]
                    X = sm.add_constant(pd.DataFrame({'Market': combined["^SET.BK"], 'Carbon': bmg}))
                    model = sm.OLS(combined[symbol], X).fit()
                    c_beta, m_beta = model.params['Carbon'], model.params['Market']
                except: c_beta, m_beta = 0.0, 1.0

                t_obj = yf.Ticker(symbol)
                full_res[symbol] = {
                    "last_price": stock_history.iloc[-1],
                    "history": stock_history,
                    "carbon_beta": c_beta,
                    "market_beta": m_beta,
                    "info": t_obj.info,
                    "news": t_obj.news[:5]
                }
        return full_res, data[ticker_list].dropna()
    except: return None, None

# --- MAIN DASHBOARD ---
st.title("🏛️ Sustainable Finance & Climate Risk Modeling")
st.markdown(f"**Asset Intelligence Terminal** | {datetime.now().strftime('%d %B %Y')}")

if tickers:
    analysis, history = fetch_analysis_data(tickers)
    
    if analysis:
        # 1. OVERVIEW COMPARISON
        cols = st.columns(len(analysis))
        for i, (symbol, d) in enumerate(analysis.items()):
            with cols[i]:
                st.metric(f"💎 {symbol}", f"{d['last_price']:,.2f}", delta=f"C-Beta: {d['carbon_beta']:.3f}")

        # 2. INDIVIDUAL DEEP DIVE TABS
        tabs = st.tabs([f"Intelligence: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                # Row 1: Fundamental Metrics
                st.markdown(f"### 🧬 {symbol} Financial Snapshot")
                f1, f2, f3, f4 = st.columns(4)
                f1.metric("P/E Ratio", d['info'].get('trailingPE', 'N/A'))
                f2.metric("Div. Yield", f"{d['info'].get('dividendYield', 0)*100:.2f}%")
                f3.metric("Market Cap", f"{d['info'].get('marketCap', 0)/1e9:.1f}B")
                f4.metric("Market Beta", f"{d['market_beta']:.2f}")

                # Row 2: Momentum & Gauge (Modern Style)
                c_l, c_r = st.columns([2, 1])
                with c_l:
                    st.subheader("📈 Price Momentum")
                    fig_mom = px.line(d['history'], labels={'value': 'Price', 'Date': ''}, color_discrete_sequence=['#2ECC71'])
                    fig_mom.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_mom, use_container_width=True)
                
                with c_r:
                    st.subheader("🔥 Carbon Sensitivity")
                    # Modern Gauge
                    risk_color = "#E74C3C" if d['carbon_beta'] > 0.05 else "#2ECC71"
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number", value = d['carbon_beta'] * 100,
                        gauge = {
                            'axis': {'range': [-50, 50], 'tickcolor': "white"},
                            'bar': {'color': risk_color},
                            'steps': [{'range': [-50, 0], 'color': "rgba(46, 204, 113, 0.1)"},
                                      {'range': [0, 50], 'color': "rgba(231, 76, 60, 0.1)"}]
                        }))
                    fig_gauge.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig_gauge, use_container_width=True)

                # Row 3: Climate Valuation (Modern Waterfall) & News
                st.divider()
                r_l, r_r = st.columns(2)
                with r_l:
                    st.subheader("💰 Equity Value Bridge (MB)")
                    val_impact = (tax_price * 1000) / wacc / 1e6
                    st.info(f"**Research:** {symbol} เสี่ยงอุทกภัย {flood_risk}% | ผลกระทบมูลค่า: -{val_impact:,.2f}M")
                    # Modern Waterfall
                    mkt_cap_mb = d['info'].get('marketCap', 1e9)/1e6
                    fig_water = go.Figure(go.Waterfall(
                        orientation = "v", x = ["Current Cap", "Climate Loss", "Adjusted Value"],
                        y = [mkt_cap_mb, -val_impact, mkt_cap_mb - val_impact],
                        measure = ["relative", "relative", "total"],
                        decreasing = {"marker":{"color":"#E74C3C"}},
                        total = {"marker":{"color":"#3498DB"}}
                    ))
                    fig_water.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig_water, use_container_width=True)

                with r_r:
                    st.subheader("📰 Latest Insights")
                    for n in d['news']:
                        st.write(f"**[{n.get('publisher','N/A')}]** {n.get('title','N/A')}")
                        st.write(f"[อ่านต่อ]({n.get('link','#')})")
                        st.divider()

        # 3. OVERALL COMPARATIVE CHART
        st.divider()
        st.subheader("📉 Normalized Momentum Comparison")
        norm_prices = (history / history.iloc[0]) * 100
        st.line_chart(norm_prices)

    else: st.error("❌ ไม่พบข้อมูล Ticker กรุณาตรวจสอบ (เช่น PTT.BK, ^GSPC)")
