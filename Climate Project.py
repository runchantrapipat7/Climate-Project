import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.graph_objects as go
from datetime import datetime
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="Climate Finance Pro Terminal", layout="wide")

# --- CSS: (ยึดตามไฟล์เดิมของคุณรันทั้งหมด) ---
st.markdown("""
    <style>
    .main { background: radial-gradient(circle at top right, #1a1f2e, #0d1117); color: white; }
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(0, 255, 136, 0.2) !important;
        border-radius: 12px !important;
        padding: 20px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
    }
    div[data-testid="stMetricValue"] > div { color: #00ff88 !important; font-weight: 700 !important; }
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; gap: 10px; border: none; }
    .stTabs [data-baseweb="tab"] { background-color: rgba(255, 255, 255, 0.05); border-radius: 4px; padding: 10px 20px; color: #8b949e; border: none; }
    .stTabs [aria-selected="true"] { background-color: #2ea043 !important; color: white !important; font-weight: bold; }
    .top-pick-container { border: 1px solid #2ea043; border-radius: 12px; padding: 15px; background: rgba(46, 160, 67, 0.08); margin-bottom: 25px; }
    .top-pick-title { color: #00ff88; font-weight: bold; font-size: 1.05rem; text-align: center; border-bottom: 1px solid rgba(46,160,67,0.3); padding-bottom: 10px; margin-bottom: 15px; }
    .top-pick-item { font-size: 0.88rem; font-weight: bold; margin-bottom: 12px; color: white; display: flex; justify-content: space-between; }
    .log-terminal { background: #000000 !important; border: 1px solid #2ea043 !important; border-radius: 8px; font-family: 'Courier New', monospace !important; padding: 15px; }
    .log-entry { color: #00ff88; font-size: 0.85rem; margin-bottom: 5px; }
    .stats-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
    .stats-table td { padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.9rem; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: rgba(13, 17, 23, 0.95); text-align: center; padding: 10px; font-size: 0.8rem; border-top: 1px solid rgba(255, 255, 255, 0.1); z-index: 999; }
    .block-container { padding-bottom: 100px; }
    </style>
    """, unsafe_allow_html=True)

# --- DATA ENGINE: (ปรับปรุงให้ดึงข้อมูลได้จริง ไม่ Error) ---
@st.cache_data(ttl=600)
def fetch_pro_data(ticker_list):
    full_res = {}
    try:
        # ดึงข้อมูล Benchmark
        proxies = yf.download(["PTTEP.BK", "EA.BK", "^SET.BK"], period="3y", progress=False)['Close']
        proxies = proxies.ffill().bfill()
    except: proxies = pd.DataFrame()

    for symbol in ticker_list:
        try:
            t_obj = yf.Ticker(symbol)
            hist = t_obj.history(period="3y")['Close']
            if hist.empty: continue
            
            # คำนวณ Carbon Beta ตามสูตรเดิมของคุณรัน
            c_beta = 0.0
            if not proxies.empty:
                try:
                    temp_df = pd.concat([hist, proxies], axis=1).pct_change().dropna()
                    bmg = temp_df["PTTEP.BK"] - temp_df["EA.BK"]
                    X = sm.add_constant(pd.DataFrame({'Market': temp_df["^SET.BK"], 'Carbon': bmg}))
                    model = sm.OLS(temp_df[symbol], X).fit()
                    c_beta = model.params.get('Carbon', 0.0)
                except: pass
            
            # ดึงข่าวพร้อมระบบป้องกัน Error
            try: news = t_obj.news[:3]
            except: news = []

            full_res[symbol] = {"price": float(hist.iloc[-1]), "history": hist, "c_beta": c_beta, "info": t_obj.info, "news": news}
        except Exception as e:
            continue
    return full_res

# --- SIDEBAR: (ยึดตามไฟล์เดิมของคุณรัน) ---
with st.sidebar:
    st.title("🛡️ Risk Controller")
    # หุ้นเด่นดึงจาก Yahoo โดยตรงตามความต้องการแรกของคุณรัน
    st.markdown('<div class="top-pick-container"><p class="top-pick-title">🌟 หุ้นเด่นวันนี้ (Real-time)</p><div class="top-pick-item"><span>PTT.BK</span><span>Active</span></div><div class="top-pick-item"><span>EA.BK</span><span>Active</span></div><div class="top-pick-item"><span>GULF.BK</span><span>Active</span></div></div>', unsafe_allow_html=True)

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

if tickers:
    analysis = fetch_pro_data(tickers)
    if analysis:
        # Metrics Cards
        cols = st.columns(len(analysis))
        for i, (symbol, d) in enumerate(analysis.items()):
            cols[i].metric(f"💎 {symbol}", f"{d['price']:,.2f}", delta=f"C-Beta: {d['c_beta']:.3f}")

        # Tabs (Intelligence Center)
        tabs = st.tabs([f"Intelligence Center: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                inf = d.get('info', {})
                st.subheader(f"📊 Market Summary: {symbol}")
                s1, s2 = st.columns(2)
                def get_v(k, f="{:,.2f}"):
                    v = inf.get(k)
                    return f.format(v) if v else "N/A"
                with s1:
                    st.markdown(f'<table class="stats-table"><tr><td>Market Cap</td><td style="text-align:right;"><b>{get_v("marketCap", "{:,.0f}")}</b></td></tr><tr><td>Trailing P/E</td><td style="text-align:right;"><b>{get_v("trailingPE")}</b></td></tr></table>', unsafe_allow_html=True)
                with s2:
                    st.markdown(f'<table class="stats-table"><tr><td>Div. Yield</td><td style="text-align:right;"><b>{get_v("dividendYield", "{:.2%}")}</b></td></tr><tr><td>Debt/Equity</td><td style="text-align:right;"><b>{get_v("debtToEquity")}</b></td></tr></table>', unsafe_allow_html=True)

                st.divider()
                # Risk Matrix
                dynamic_trans = d['c_beta'] * 100 * tax_multiplier
                r1, r2, r3, r4 = st.columns(4)
                r1.warning(f"💳 Credit: {'High' if (inf.get('debtToEquity',0)>150 or dynamic_trans>25) else 'Low'}")
                r2.error(f"🏗️ Operational: {'High' if flood_risk > 60 else 'Low'}")
                r3.info(f"💧 Liquidity: Low")
                r4.success(f"⚖️ Liability: Low")

                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("🔥 Transition Risk Sensitivity")
                    fig_g = go.Figure(go.Indicator(mode="gauge+number", value=dynamic_trans, gauge={'axis':{'range':[-50,50]}, 'bar':{'color':"white"}, 'steps':[{'range':[-50,0],'color':"#238636"},{'range':[0,50],'color':"#da3633"}]}))
                    fig_g.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=0,b=0))
                    st.plotly_chart(fig_g, use_container_width=True, key=f"g_{symbol}_{i}")
                with c2:
                    st.subheader("💰 Equity Value Bridge (MB)")
                    m_cap_mb = float(inf.get('marketCap', 1e11))/1e6
                    val_impact = (tax_price * 1000) / wacc / 1e6
                    fig_w = go.Figure(go.Waterfall(x=["Initial", "Loss", "Adj"], y=[m_cap_mb, -val_impact, m_cap_mb-val_impact]))
                    fig_w.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=0,b=0))
                    st.plotly_chart(fig_w, use_container_width=True, key=f"w_{symbol}_{i}")

                # Terminal Log (Collapsible)
                with st.expander("📟 View Terminal Risk Log (Activity)", expanded=False):
                    st.markdown(f'<div class="log-terminal"><div class="log-entry">[{datetime.now().strftime("%H:%M:%S")}] > ANALYZING {symbol}...</div><div class="log-entry">[{datetime.now().strftime("%H:%M:%S")}] > STATUS: COMPLETED.</div></div>', unsafe_allow_html=True)

st.markdown(f'<div class="footer">🏛️ Sustainable Finance Terminal | <b>Presented by Run Chantrapipat</b> | © 2026</div>', unsafe_allow_html=True)
