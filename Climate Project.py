import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.graph_objects as go
from datetime import datetime
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="Sustainable Finance Intelligence", layout="wide")

# --- CSS: Ultimate Dashboard Theme ---
st.markdown("""
    <style>
    .main { background-color: #0b0e14; color: #ffffff; }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 16px; padding: 20px;
    }
    div[data-testid="stMetricValue"] > div { color: #00ff88 !important; font-weight: 700; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: rgba(255, 255, 255, 0.05); border-radius: 8px;
        padding: 10px 30px; color: #aaa; border: none;
    }
    .stTabs [aria-selected="true"] { 
        background: linear-gradient(90deg, #00ff88 0%, #00bd68 100%); color: #000 !important; 
    }
    h1, h2, h3 { font-family: 'Inter', sans-serif; letter-spacing: -0.5px; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Risk Intelligence")
    st.header("🔍 ระบุชื่อหุ้นหรือกองทุน (Stock or Bond)")
    t1 = st.text_input("Asset 1", "PTT.BK")
    t2 = st.text_input("Asset 2", "EA.BK")
    t3 = st.text_input("Asset 3", "")
    tickers = [t.strip().upper() for t in [t1, t2, t3] if t.strip()]

    st.divider()
    st.header("🌍 Scenario & Policy (TCFD)")
    scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
    tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    flood_risk = st.slider("Flood Exposure (%)", 0, 100, 45)
    wacc = st.slider("WACC (%)", 5.0, 15.0, 8.0) / 100

# --- DATA ENGINE ---
@st.cache_data(ttl=600)
def fetch_terminal_data(ticker_list):
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
            
            # คำนวณ Carbon Beta (Transition Risk)
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
    analysis = fetch_terminal_data(tickers)
    
    if analysis:
        # Comparative Cards
        cols = st.columns(len(analysis))
        for i, (symbol, d) in enumerate(analysis.items()):
            cols[i].metric(f"💎 {symbol}", f"{d['price']:,.2f}", delta=f"C-Beta: {d['c_beta']:.3f}")

        # Deep Dive Analysis
        tabs = st.tabs([f"Terminal: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                # Row 1: Charts
                c1, c2 = st.columns([1, 1.2])
                
                with c1:
                    st.subheader("🔥 Transition Risk Sensitivity")
                    # MODERN GAUGE
                    val = d['c_beta'] * 100
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number", value = val,
                        title = {'text': "Carbon Beta Index", 'font': {'size': 16}},
                        gauge = {
                            'axis': {'range': [-50, 50], 'tickwidth': 1},
                            'bar': {'color': "#00ff88" if val < 5 else "#ffcc00" if val < 15 else "#ff4b4b"},
                            'steps': [
                                {'range': [-50, 5], 'color': 'rgba(0, 255, 136, 0.1)'},
                                {'range': [5, 15], 'color': 'rgba(255, 204, 0, 0.1)'},
                                {'range': [15, 50], 'color': 'rgba(255, 75, 75, 0.1)'}],
                            'threshold': {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': val}
                        }))
                    fig_gauge.update_layout(height=380, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=50, b=20))
                    st.plotly_chart(fig_gauge, use_container_width=True, key=f"g_{symbol}_{i}")

                with c2:
                    st.subheader("💰 Equity Value Bridge (MB)")
                    # MODERN WATERFALL
                    m_cap = d['info'].get('marketCap', 1e11)
                    mkt_cap_mb = float(m_cap)/1e6
                    val_impact = (tax_price * 1000) / wacc / 1e6
                    
                    fig_water = go.Figure(go.Waterfall(
                        orientation = "v",
                        measure = ["relative", "relative", "total"],
                        x = ["Initial Cap", "Climate Risk", "Adj. Value"],
                        y = [mkt_cap_mb, -val_impact, mkt_cap_mb - val_impact],
                        increasing = {"marker":{"color":"#00ff88"}},
                        decreasing = {"marker":{"color":"#ff4b4b"}},
                        totals = {"marker":{"color":"#00a2ff"}}
                    ))
                    fig_water.update_layout(height=380, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig_water, use_container_width=True, key=f"w_{symbol}_{i}")

                # Row 2: Stats & News
                st.divider()
                s1, s2 = st.columns([2, 1])
                with s1:
                    st.subheader("📈 Price Momentum")
                    st.line_chart(d['history'], height=250)
                with s2:
                    st.subheader("📰 Market Intelligence")
                    for n in d['news']:
                        st.caption(f"**{n.get('publisher')}**")
                        st.write(n.get('title'))
                        st.divider()
    else:
        st.error("ไม่พบข้อมูล Ticker ที่ระบุ กรุณาลองใหม่อีกครั้ง")
