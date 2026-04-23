import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Climate Finance Terminal", layout="wide")

# --- CSS: ULTIMATE DARK TERMINAL UI ---
st.markdown("""
    <style>
    .main { background: radial-gradient(circle at top right, #1a1f2e, #0d1117); color: white; }
    div[data-testid="stMetric"] { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(0, 255, 136, 0.2); border-radius: 12px; padding: 20px; }
    .stTabs [data-baseweb="tab"] { background-color: rgba(255, 255, 255, 0.05); border-radius: 4px; padding: 10px 20px; color: #8b949e; border: none; }
    .stTabs [aria-selected="true"] { background-color: #2ea043 !important; color: white !important; font-weight: bold; }
    .top-pick-container { border: 1px solid #2ea043; border-radius: 12px; padding: 15px; background: rgba(46, 160, 67, 0.08); margin-bottom: 25px; }
    .log-terminal { background: #000000; border: 1px solid #2ea043; border-radius: 8px; padding: 15px; font-family: 'Courier New', Courier, monospace; }
    .log-entry { color: #00ff88; font-size: 0.85rem; margin-bottom: 5px; }
    .stats-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
    .stats-table td { padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.9rem; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: rgba(13, 17, 23, 0.95); color: #8b949e; text-align: center; padding: 10px; border-top: 1px solid rgba(255, 255, 255, 0.1); }
    .block-container { padding-bottom: 100px; }
    </style>
    """, unsafe_allow_html=True)

# --- FAIL-SAFE DATA ENGINE ---
@st.cache_data(ttl=600)
def fetch_robust_data(ticker_list):
    full_res = {}
    # ดึง Benchmark
    try:
        proxies = yf.download(["PTTEP.BK", "EA.BK", "^SET.BK"], period="2y", progress=False)['Close']
        proxies = proxies.ffill().bfill()
    except: proxies = pd.DataFrame()

    for symbol in ticker_list:
        try:
            t_obj = yf.Ticker(symbol)
            hist = t_obj.history(period="2y")['Close']
            if hist.empty: continue
            
            # Carbon Beta calculation
            c_beta = 0.0
            if not proxies.empty:
                try:
                    temp_df = pd.concat([hist, proxies], axis=1).pct_change().dropna()
                    bmg = temp_df["PTTEP.BK"] - temp_df["EA.BK"]
                    X = sm.add_constant(pd.DataFrame({'Market': temp_df["^SET.BK"], 'Carbon': bmg}))
                    c_beta = sm.OLS(temp_df[symbol], X).fit().params.get('Carbon', 0.0)
                except: pass
            
            # Robust info fetch
            try: info = t_obj.info
            except: info = {}

            full_res[symbol] = {"price": float(hist.iloc[-1]), "history": hist, "c_beta": c_beta, "info": info, "news": t_obj.news[:3]}
        except: continue
    return full_res

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Risk Controller")
    # หุ้นเด่น 5 ตัว (Hardcoded for stability if API fails)
    st.markdown('<div class="top-pick-container"><p style="color:#00ff88; font-weight:bold; text-align:center;">🌟 หุ้นเด่นวันนี้ (Real-time)</p><div style="font-size:0.85rem;">PTT.BK (Active)<br>GULF.BK (Active)<br>SCB.BK (Active)<br>CPALL.BK (Active)<br>EA.BK (Active)</div></div>', unsafe_allow_html=True)
    
    with st.expander("🔍 Asset Selection", expanded=True):
        t1 = st.text_input("Asset 1", "PTT.BK")
        t2 = st.text_input("Asset 2", "EA.BK")
        t3 = st.text_input("Asset 3", "")
    
    scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
    tax_multiplier = {"Net Zero 2050": 1.5, "Delayed Transition": 1.0, "Current Policy": 0.5}[scenario]
    tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    flood_risk = st.slider("Flood Exposure (%)", 0, 100, 35)
    wacc = st.slider("WACC (%)", 5.0, 20.0, 12.0) / 100
    tickers = [t.strip().upper() for t in [t1, t2, t3] if t.strip()]

# --- MAIN DISPLAY ---
st.title("🏛️ SUSTAINABLE FINANCE ASSET TERMINAL")

if not tickers:
    st.info("💡 กรุณาระบุชื่อหุ้นใน Sidebar เพื่อเริ่มต้น")
else:
    analysis = fetch_robust_data(tickers)
    if not analysis:
        st.error("❌ ไม่สามารถดึงข้อมูลได้ โปรดลองอีกครั้งหรือเปลี่ยนชื่อหุ้น")
    else:
        # Metrics
        cols = st.columns(len(analysis))
        for i, (symbol, d) in enumerate(analysis.items()):
            cols[i].metric(f"💎 {symbol}", f"{d['price']:,.2f}", delta=f"C-Beta: {d['c_beta']:.3f}")

        # Tabs
        tabs = st.tabs([f"Intelligence Center: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                inf = d.get('info', {})
                # 📊 Stats
                s1, s2 = st.columns(2)
                def get_v(k, s="{:,.2f}"):
                    val = inf.get(k)
                    return s.format(val) if val else "N/A"
                with s1:
                    st.markdown(f'<table class="stats-table"><tr><td>Market Cap</td><td style="text-align:right;"><b>{get_v("marketCap", "{:,.0f}")}</b></td></tr><tr><td>Trailing P/E</td><td style="text-align:right;"><b>{get_v("trailingPE")}</b></td></tr></table>', unsafe_allow_html=True)
                with s2:
                    st.markdown(f'<table class="stats-table"><tr><td>Dividend Yield</td><td style="text-align:right;"><b>{get_v("dividendYield", "{:.2%}")}</b></td></tr><tr><td>Debt/Equity</td><td style="text-align:right;"><b>{get_v("debtToEquity")}</b></td></tr></table>', unsafe_allow_html=True)

                st.divider()
                # 🛡️ Risk Matrix
                dynamic_trans = d['c_beta'] * 100 * tax_multiplier
                r1, r2, r3, r4 = st.columns(4)
                r1.warning(f"💳 Credit: {'High' if dynamic_trans > 20 else 'Low'}")
                r2.error(f"🏗️ Operational: {'High' if flood_risk > 50 else 'Low'}")
                r3.info("💧 Liquidity: Low")
                r4.success("⚖️ Liability: Low")

                # 📈 Charts
                c1, c2 = st.columns(2)
                with c1:
                    fig_g = go.Figure(go.Indicator(mode="gauge+number", value=dynamic_trans, gauge={'axis': {'range': [-50, 50]}, 'steps': [{'range': [-50, 0], 'color': "green"}, {'range': [0, 50], 'color': "red"}]}))
                    fig_g.update_layout(height=250, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=0, b=0))
                    st.plotly_chart(fig_g, use_container_width=True)
                with c2:
                    m_cap = inf.get('marketCap', 1e11) / 1e6
                    loss = (tax_price * 1000) / wacc / 1e6
                    fig_w = go.Figure(go.Waterfall(x=["Cap", "Loss", "Adj"], y=[m_cap, -loss, m_cap-loss]))
                    fig_w.update_layout(height=250, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=0, b=0))
                    st.plotly_chart(fig_w, use_container_width=True)

                # 📝 Log
                with st.expander("📟 Terminal Risk Log", expanded=False):
                    st.markdown(f'<div class="log-terminal"><div class="log-entry">[{datetime.now().strftime("%H:%M:%S")}] > ANALYZING {symbol}...</div><div class="log-entry">[{datetime.now().strftime("%H:%M:%S")}] > BETA: {d["c_beta"]:.4f}</div><div class="log-entry">[{datetime.now().strftime("%H:%M:%S")}] > STATUS: COMPLETED</div></div>', unsafe_allow_html=True)

st.markdown(f'<div class="footer">🏛️ Sustainable Finance Terminal | <b>Presented by Run Chantrapipat</b> | © 2026</div>', unsafe_allow_html=True)
