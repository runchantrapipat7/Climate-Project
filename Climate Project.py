import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Climate Finance Pro Terminal", layout="wide")

# --- CSS: ULTIMATE MODERN UI ---
st.markdown("""
    <style>
    .main { background: radial-gradient(circle at top right, #1a1f2e, #0d1117); color: white; }
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: rgba(255, 255, 255, 0.05); 
        border-radius: 4px; padding: 10px 25px; color: #8b949e; border: none;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #2ea043 !important; color: white !important; font-weight: bold;
    }
    .top-pick-container {
        border: 1px solid #2ea043; border-radius: 12px; padding: 15px;
        background: rgba(46, 160, 67, 0.08); box-shadow: 0 0 15px rgba(46, 160, 67, 0.15);
        margin-bottom: 25px;
    }
    .top-pick-header-box { padding-bottom: 12px; margin-bottom: 15px; text-align: center; border-bottom: 1px solid rgba(46, 160, 67, 0.3); }
    .top-pick-title { color: #00ff88; font-weight: bold; font-size: 1.05rem; margin: 0; }
    .top-pick-item { font-size: 0.88rem; font-weight: bold; margin-bottom: 12px; color: white; display: flex; justify-content: space-between; align-items: center; }
    .active-vol-label { color: #8b949e; font-weight: normal; font-size: 0.72rem; }
    .top-pick-subtext { font-size: 0.7rem; color: #8b949e; margin-top: 15px; text-align: center; opacity: 0.8; }
    div[data-testid="stMetric"] { background: rgba(255, 255, 255, 0.03) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; border-radius: 12px; padding: 15px; }
    .insight-card { background: rgba(0, 255, 136, 0.05); border-left: 4px solid #00ff88; padding: 15px; border-radius: 8px; margin-top: 10px; font-size: 0.9rem; }
    .risk-card { background: rgba(255, 75, 75, 0.05); border-left: 4px solid #ff4b4b; padding: 15px; border-radius: 8px; margin-top: 10px; font-size: 0.9rem; }
    .stats-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
    .stats-table td { padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.9rem; }
    .stats-label { color: #8b949e; }
    .stats-value { text-align: right; font-weight: bold; color: #ffffff; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: rgba(13, 17, 23, 0.95); color: #8b949e; text-align: center; padding: 10px; font-size: 0.8rem; border-top: 1px solid rgba(255, 255, 255, 0.1); z-index: 999; }
    </style>
    """, unsafe_allow_html=True)

# --- DYNAMIC TOP PICKS ENGINE ---
@st.cache_data(ttl=3600)
def get_real_top_picks_5():
    candidate_tickers = ["PTT.BK", "CPALL.BK", "AOT.BK", "KBANK.BK", "EA.BK", "ADVANC.BK", "GULF.BK", "SCB.BK"]
    picks = []
    for t in candidate_tickers:
        try:
            ticker = yf.Ticker(t)
            data = ticker.history(period="1d")
            if not data.empty: picks.append({"symbol": t, "volume": data['Volume'].iloc[-1]})
        except: continue
    return sorted(picks, key=lambda x: x['volume'], reverse=True)[:5]

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Risk Controller")
    top_stocks = get_real_top_picks_5()
    stocks_html = "".join([f'<div class="top-pick-item"><span>{s["symbol"]}</span><span class="active-vol-label">Active Vol.</span></div>' for s in top_stocks])
    st.markdown(f'<div class="top-pick-container"><div class="top-pick-header-box"><p class="top-pick-title">🌟 หุ้นเด่นวันนี้ (Real-time)</p></div>{stocks_html}<div class="top-pick-subtext">อัปเดตข้อมูลจาก Yahoo Finance รายวัน</div></div>', unsafe_allow_html=True)

    with st.expander("🔍 ระบุชื่อหุ้น (Asset Selection)", expanded=True):
        t1 = st.text_input("Asset 1", "PTT.BK")
        t2 = st.text_input("Asset 2", "EA.BK")
        t3 = st.text_input("Asset 3", "TPIPP.BK")
    
    st.divider()
    with st.expander("🌍 Scenario Policy (TCFD)", expanded=True):
        scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
        tax_multiplier = {"Net Zero 2050": 1.5, "Delayed Transition": 1.0, "Current Policy": 0.5}[scenario]
        tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    st.divider()
    with st.expander("⚙️ Physical Risk Parameters", expanded=True):
        flood_risk = st.slider("Flood Exposure (%)", 0, 100, 45)
        wacc = st.slider("WACC (%)", 5.0, 15.0, 8.0) / 100

    tickers = [t.strip().upper() for t in [t1, t2, t3] if t.strip()]

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
            full_res[symbol] = {"price": float(hist.iloc[-1]), "history": hist, "c_beta": c_beta, "info": t_obj.info, "news": t_obj.news[:3]}
        except: continue
    return full_res

# --- MAIN DISPLAY ---
st.title("🏛️ SUSTAINABLE FINANCE ASSET TERMINAL")

if tickers:
    analysis = fetch_pro_data(tickers)
    if analysis:
        cols = st.columns(len(analysis))
        for i, (symbol, d) in enumerate(analysis.items()):
            cols[i].metric(f"💎 {symbol}", f"{d['price']:,.2f}", delta=f"C-Beta: {d['c_beta']:.3f}")

        tabs = st.tabs([f"Intelligence Center: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                # 📊 สถิติเดิม
                st.subheader(f"📊 Market Summary: {symbol}")
                inf = d.get('info', {})
                s1, s2 = st.columns(2)
                def fmt(key, style="{:,.2f}"):
                    val = inf.get(key)
                    return style.format(val) if val is not None else "N/A"
                with s1:
                    st.markdown(f'<table class="stats-table"><tr><td class="stats-label">Market Cap</td><td class="stats-value">{fmt("marketCap", "{:,.0f}")}</td></tr><tr><td class="stats-label">Trailing P/E</td><td class="stats-value">{fmt("trailingPE")}</td></tr><tr><td class="stats-label">Beta (5Y Monthly)</td><td class="stats-value">{fmt("beta")}</td></tr></table>', unsafe_allow_html=True)
                with s2:
                    st.markdown(f'<table class="stats-table"><tr><td class="stats-label">Profit Margin</td><td class="stats-value">{fmt("profitMargins", "{:.2%}")}</td></tr><tr><td class="stats-label">Dividend Yield</td><td class="stats-value">{fmt("dividendYield", "{:.2%}")}</td></tr><tr><td class="stats-label">Debt/Equity</td><td class="stats-value">{fmt("debtToEquity")}</td></tr></table>', unsafe_allow_html=True)

                # 🛡️ ส่วนที่เพิ่มใหม่: Comprehensive Risk Matrix
                st.divider()
                st.subheader("🛡️ Comprehensive Climate Risk Matrix")
                
                # คำนวณ Risk แบบละเอียดตามทฤษฎีที่คุณส่งมา
                de_ratio = inf.get('debtToEquity', 100)
                dynamic_trans = d['c_beta'] * 100 * tax_multiplier
                
                # Logic การประเมิน
                credit_risk = "High" if (de_ratio > 150 or dynamic_trans > 25) else "Medium" if de_ratio > 80 else "Low"
                op_risk = "High" if flood_risk > 60 else "Medium" if flood_risk > 30 else "Low"
                liq_risk = "High" if inf.get('marketCap', 1e11) < 1e9 else "Low"
                
                r1, r2, r3, r4 = st.columns(4)
                r1.warning(f"💳 Credit Risk: {credit_risk}")
                r2.error(f"🏗️ Operational: {op_risk}")
                r3.info(f"💧 Liquidity: {liq_risk}")
                r4.success(f"⚖️ Liability: Low")

                st.divider()
                # 📈 กราฟเดิม (แก้ไขให้ขยับ)
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("🔥 Transition Risk Sensitivity")
                    fig_gauge = go.Figure(go.Indicator(mode = "gauge+number", value = dynamic_trans,
                        gauge = {'axis': {'range': [-50, 50], 'tickcolor': "white"}, 'bar': {'color': "white"},
                        'steps': [{'range': [-50, 0], 'color': '#238636'}, {'range': [0, 20], 'color': '#f1e05a'}, {'range': [20, 50], 'color': '#da3633'}]}))
                    fig_gauge.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=0, b=0))
                    st.plotly_chart(fig_gauge, use_container_width=True, key=f"g_{symbol}_{i}")
                    st.markdown(f'<div class="risk-card"><b>Insight:</b> Transition Impact ต่อ Asset นี้คือ <b>{dynamic_trans:.2f}</b></div>', unsafe_allow_html=True)
                
                with c2:
                    st.subheader("💰 Equity Value Bridge (MB)")
                    mkt_cap_mb = float(inf.get('marketCap', 1e11))/1e6
                    val_impact = (tax_price * 1000) / wacc / 1e6
                    adj_val = mkt_cap_mb - val_impact
                    fig_water = go.Figure(go.Waterfall(orientation = "v", measure = ["relative", "relative", "total"],
                        x = ["Initial Cap", "Climate Loss", "Adj. Value"], y = [mkt_cap_mb, -val_impact, adj_val],
                        text = [f"{mkt_cap_mb:,.0f}", f"-{val_impact:,.0f}", f"{adj_val:,.0f}"], textposition = "outside",
                        increasing = {"marker":{"color":"#2ea043"}}, decreasing = {"marker":{"color":"#da3633"}}, totals = {"marker":{"color":"#1f6feb"}}))
                    fig_water.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=0, b=0))
                    st.plotly_chart(fig_water, use_container_width=True, key=f"w_{symbol}_{i}")
                    st.markdown(f'<div class="insight-card"><b>Insight:</b> มูลค่าพื้นฐานหลังปรับปรุง Climate Risk คือ <b>{adj_val:,.2f} MB</b></div>', unsafe_allow_html=True)
                
                st.divider()
                st.subheader("📈 Price Momentum & News")
                m1, m2 = st.columns([1.5, 1])
                with m1: st.line_chart(d['history'], height=250)
                with m2:
                    if d['news']:
                        for n in d['news']:
                            st.write(f"**{n.get('publisher','News')}**: {n.get('title')}")
                            st.divider()

# --- FOOTER ---
st.markdown(f'<div class="footer">🏛️ Sustainable Finance Terminal | <b>Presented by Run Chantrapipat</b> | © 2026</div>', unsafe_allow_html=True)
