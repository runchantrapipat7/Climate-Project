import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Climate Finance Intelligence", layout="wide")

# --- CSS: High-End Terminal UI ---
st.markdown("""
    <style>
    .main { background: radial-gradient(circle at top right, #1a1f2e, #0d1117); }
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px; padding: 20px;
    }
    div[data-testid="stMetricValue"] > div { color: #00ff88 !important; }
    .stTabs [aria-selected="true"] { background: #2ea043 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: ALL FEATURES INCLUDED ---
with st.sidebar:
    st.title("🛡️ Portfolio Risk Control")
    
    # 1. หัวข้อที่คุณต้องการ (คืนค่าให้แล้วครับ)
    st.header("🔍 ระบุชื่อหุ้นหรือกองทุน (Stock or Bond)")
    t1 = st.text_input("Asset 1", "PTT.BK")
    t2 = st.text_input("Asset 2", "EA.BK")
    t3 = st.text_input("Asset 3", "")
    tickers = [t.strip().upper() for t in [t1, t2, t3] if t.strip()]

    st.divider()
    
    # 2. Climate Scenario
    st.header("🌍 Scenario & Policy (TCFD)")
    scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
    tax_multiplier = {"Net Zero 2050": 1.5, "Delayed Transition": 1.0, "Current Policy": 0.5}[scenario]
    tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    # 3. Physical Risk
    flood_risk = st.slider("Flood Exposure (%)", 0, 100, 45)
    wacc = st.slider("WACC (%)", 5.0, 15.0, 8.0) / 100

# --- DATA ENGINE ---
@st.cache_data(ttl=600)
def fetch_pro_data(ticker_list):
    full_res = {}
    try:
        proxies = yf.download(["PTTEP.BK", "EA.BK", "^SET.BK"], period="3y", progress=False)['Close']
        proxies = proxies.ffill().bfill()
    except: proxies = pd.DataFrame()

    for symbol in ticker_list:
        try:
            t_obj = yf.Ticker(symbol)
            hist = t_obj.history(period="3y")['Close']
            if hist.empty: continue
            
            c_beta = 0.0
            if not proxies.empty:
                try:
                    temp_df = pd.concat([hist, proxies], axis=1).pct_change().dropna()
                    bmg = temp_df["PTTEP.BK"] - temp_df["EA.BK"]
                    X = sm.add_constant(pd.DataFrame({'Market': temp_df["^SET.BK"], 'Carbon': bmg}))
                    model = sm.OLS(temp_df[symbol], X).fit()
                    c_beta = model.params.get('Carbon', 0.0)
                except: pass

            full_res[symbol] = {
                "price": float(hist.iloc[-1]),
                "history": hist,
                "c_beta": c_beta,
                "info": t_obj.info if t_obj.info else {},
                "news": t_obj.news[:3] if t_obj.news else []
            }
        except: continue
    return full_res

# --- MAIN DISPLAY ---
st.title("🏛️ SUSTAINABLE FINANCE & CLIMATE RISK MODELING")

if tickers:
    analysis = fetch_pro_data(tickers)
    if analysis:
        # Overview Cards
        cols = st.columns(len(analysis))
        for i, (symbol, d) in enumerate(analysis.items()):
            cols[i].metric(f"💎 {symbol}", f"{d['price']:,.2f}", delta=f"C-Beta: {d['c_beta']:.3f}")

        # Individual Analysis Tabs
        tabs = st.tabs([f"Intelligence: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                c1, c2 = st.columns(2)
                
                with c1:
                    st.subheader("🔥 Transition Risk Sensitivity")
                    # DYNAMIC GAUGE (เชื่อมโยง Sidebar แล้ว)
                    risk_val = d['c_beta'] * 100 * tax_multiplier
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number", value = risk_val,
                        gauge = {
                            'axis': {'range': [-50, 50]},
                            'bar': {'color': "white"},
                            'steps': [
                                {'range': [-50, 0], 'color': '#238636'},
                                {'range': [0, 20], 'color': '#f1e05a'},
                                {'range': [20, 50], 'color': '#da3633'}]
                        }))
                    fig_gauge.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig_gauge, use_container_width=True, key=f"gauge_{symbol}")

                with c2:
                    st.subheader("💰 Equity Value Bridge (MB)")
                    # PREMIUM WATERFALL (ทันสมัยและมี Data Labels)
                    m_cap = d['info'].get('marketCap', 1e11)
                    mkt_cap_mb = float(m_cap)/1e6
                    val_impact = (tax_price * 1000) / wacc / 1e6
                    
                    fig_water = go.Figure(go.Waterfall(
                        orientation = "v",
                        measure = ["relative", "relative", "total"],
                        x = ["Starting Cap", "Climate Loss", "Adj. Value"],
                        y = [mkt_cap_mb, -val_impact, mkt_cap_mb - val_impact],
                        text = [f"{mkt_cap_mb:,.0f}", f"-{val_impact:,.0f}", f"{(mkt_cap_mb-val_impact):,.0f}"],
                        textposition = "outside",
                        increasing = {"marker":{"color":"#2ea043"}},
                        decreasing = {"marker":{"color":"#da3633"}},
                        totals = {"marker":{"color":"#1f6feb"}}
                    ))
                    fig_water.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig_water, use_container_width=True, key=f"water_{symbol}")

                st.divider()
                
                # Combined Insights & Momentum
                m1, m2 = st.columns([1.5, 1])
                with m1:
                    st.subheader("📈 Price Momentum (3Y)")
                    st.line_chart(d['history'], height=250)
                with m2:
                    st.subheader("📰 Combined Insights")
                    if d['news']:
                        for n in d['news']:
                            st.write(f"**{n.get('publisher','Source')}**: {n.get('title','No Title')}")
                            st.divider()
                    else: st.info(f"No recent news. Beta is {d['c_beta']:.4f}")
