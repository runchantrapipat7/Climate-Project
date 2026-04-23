import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.graph_objects as go
from datetime import datetime
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="Climate Finance Pro", layout="wide")

# --- CSS: HIGH-END MODERN UI (Glassmorphism) ---
st.markdown("""
    <style>
    .main { background: radial-gradient(circle at top right, #1a1f2e, #0d1117); }
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px; padding: 20px;
    }
    div[data-testid="stMetricValue"] > div { color: #00ff88 !important; font-weight: 600; }
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: rgba(255, 255, 255, 0.05); 
        border-radius: 8px; padding: 10px 25px; color: #8b949e; border: none;
    }
    .stTabs [aria-selected="true"] { 
        background: linear-gradient(135deg, #2ea043 0%, #238636 100%); color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Risk Intelligence")
    st.header("🔍 ระบุชื่อหุ้นหรือกองทุน (Stock or Bond)")
    t1 = st.text_input("Asset 1", "PTT.BK")
    t2 = st.text_input("Asset 2", "TPIPP.BK")
    t3 = st.text_input("Asset 3", "")
    tickers = [t.strip().upper() for t in [t1, t2, t3] if t.strip()]

    st.divider()
    st.header("🌍 Scenario & Policy (TCFD)")
    scenario = st.select_slider("Ambition", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
    tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    flood_risk = st.slider("Flood Exposure (%)", 0, 100, 45)
    wacc = st.slider("WACC (%)", 5.0, 15.0, 8.0) / 100

# --- DATA ENGINE ---
@st.cache_data(ttl=600)
def fetch_pro_data(ticker_list):
    full_res = {}
    try:
        # ดึงดัชนีอ้างอิงเพื่อใช้คำนวณ Carbon Beta
        proxies = yf.download(["PTTEP.BK", "EA.BK", "^SET.BK"], period="3y", progress=False)['Close']
        proxies = proxies.ffill().bfill()
    except: proxies = pd.DataFrame()

    for symbol in ticker_list:
        try:
            t_obj = yf.Ticker(symbol)
            hist = t_obj.history(period="3y")['Close']
            if hist.empty: continue
            
            # Transition Risk Modeling
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
st.markdown(f"**Asset Intelligence Terminal** | {datetime.now().strftime('%d %B %Y')}")

if tickers:
    analysis = fetch_pro_data(tickers)
    
    if analysis:
        # Comparison Overview
        cols = st.columns(len(analysis))
        for i, (symbol, d) in enumerate(analysis.items()):
            cols[i].metric(f"💎 {symbol}", f"{d['price']:,.2f}", delta=f"C-Beta: {d['c_beta']:.3f}")

        # Deep Dive Tabs
        tabs = st.tabs([f"Intelligence: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                c1, c2 = st.columns([1, 1.2])
                
                with c1:
                    st.subheader("🔥 Transition Risk Sensitivity")
                    # FIXED GAUGE: แก้ไข ValueError โดยการจัดพารามิเตอร์ใหม่
                    val = float(d['c_beta'] * 100)
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = val,
                        gauge = {
                            'axis': {'range': [-50, 50], 'tickwidth': 1, 'tickcolor': "white"},
                            'bar': {'color': "rgba(255, 255, 255, 0.8)"},
                            'bgcolor': "rgba(0,0,0,0.1)",
                            'steps': [
                                {'range': [-50, 0], 'color': '#238636'},   # Green (Low Risk)
                                {'range': [0, 20], 'color': '#f1e05a'},    # Yellow (Med Risk)
                                {'range': [20, 50], 'color': '#da3633'}    # Red (High Risk)
                            ],
                            'threshold': {
                                'line': {'color': "white", 'width': 4},
                                'thickness': 0.75,
                                'value': val
                            }
                        }
                    ))
                    fig_gauge.update_layout(height=380, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=50, b=20, l=30, r=30))
                    st.plotly_chart(fig_gauge, use_container_width=True, key=f"gauge_{symbol}_{i}")

                with c2:
                    st.subheader("💰 Equity Value Bridge (MB)")
                    # FIXED WATERFALL: จัดการพารามิเตอร์ให้เสถียร
                    m_cap = d['info'].get('marketCap', 1e11)
                    mkt_cap_mb = float(m_cap)/1e6
                    val_impact = (float(tax_price) * 1000) / float(wacc) / 1e6
                    
                    fig_water = go.Figure(go.Waterfall(
                        orientation = "v",
                        measure = ["relative", "relative", "total"],
                        x = ["Initial Cap", "Climate Loss", "Adjusted Fair Value"],
                        y = [mkt_cap_mb, -val_impact, mkt_cap_mb - val_impact],
                        connector = {"line":{"color":"rgba(255,255,255,0.3)", "width": 1}},
                        increasing = {"marker":{"color":"#2ea043"}},
                        decreasing = {"marker":{"color":"#da3633"}},
                        totals = {"marker":{"color":"#1f6feb"}}
                    ))
                    fig_water.update_layout(height=380, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=50, b=20))
                    st.plotly_chart(fig_water, use_container_width=True, key=f"water_{symbol}_{i}")

                st.divider()
                # Momentum & News
                m1, m2 = st.columns([1.5, 1])
                with m1:
                    st.subheader("📈 Price Momentum (3Y)")
                    st.line_chart(d['history'], height=250)
                with m2:
                    st.subheader("📰 Combined Insights")
                    for n in d['news']:
                        st.caption(f"**{n.get('publisher','N/A')}**")
                        st.write(n.get('title','N/A'))
                        st.divider()
    else:
        st.error("❌ ไม่พบข้อมูล Ticker หรือการเชื่อมต่อฐานข้อมูลขัดข้อง กรุณาลองใหม่อีกครั้ง")
