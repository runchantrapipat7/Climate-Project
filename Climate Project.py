import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Climate Finance Intelligence Pro", layout="wide")

# --- CSS: ULTIMATE DARK MODE & TABLE STYLING ---
st.markdown("""
    <style>
    .main { background: radial-gradient(circle at top right, #1a1f2e, #0d1117); color: white; }
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px; padding: 15px;
    }
    .insight-card {
        background: rgba(0, 255, 136, 0.05); border-left: 4px solid #00ff88;
        padding: 15px; border-radius: 8px; margin-top: 10px; font-size: 0.9rem;
    }
    .risk-card {
        background: rgba(255, 75, 75, 0.05); border-left: 4px solid #ff4b4b;
        padding: 15px; border-radius: 8px; margin-top: 10px; font-size: 0.9rem;
    }
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: rgba(13, 17, 23, 0.9); color: #8b949e;
        text-align: center; padding: 10px; font-size: 0.8rem;
        border-top: 1px solid rgba(255, 255, 255, 0.1); z-index: 999;
    }
    /* Yahoo Finance Style Table */
    .stats-table { width: 100%; border-collapse: collapse; margin: 10px 0; }
    .stats-table td { padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.9rem; }
    .stats-label { color: #8b949e; }
    .stats-value { text-align: right; font-weight: bold; color: #adbac7; }
    .block-container { padding-bottom: 60px; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: ALL FEATURES PRESERVED ---
with st.sidebar:
    st.title("🛡️ Risk Controller")
    with st.expander("🔍 Asset Selection", expanded=True):
        t1 = st.text_input("Asset 1", "PTT.BK")
        t2 = st.text_input("Asset 2", "EA.BK")
        t3 = st.text_input("Asset 3", "")
    st.divider()
    with st.expander("🌍 Climate Scenarios", expanded=True):
        scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
        tax_multiplier = {"Net Zero 2050": 1.5, "Delayed Transition": 1.0, "Current Policy": 0.5}[scenario]
        tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    st.divider()
    with st.expander("⚙️ Advanced Parameters", expanded=True):
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
            full_res[symbol] = {"price": float(hist.iloc[-1]), "history": hist, "c_beta": c_beta, "info": t_obj.info if t_obj.info else {}, "news": t_obj.news[:3] if t_obj.news else []}
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

        tabs = st.tabs([f"Intelligence: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                # --- NEW: Yahoo Finance Style Statistics Section ---
                st.subheader(f"📊 Market Summary: {symbol}")
                inf = d['info']
                s1, s2 = st.columns(2)
                
                # ฟังก์ชันช่วยจัดรูปแบบข้อมูล
                def get_val(key, fmt="{:,.2f}"):
                    val = inf.get(key)
                    return fmt.format(val) if val is not None else "N/A"

                with s1:
                    st.markdown(f"""<table class="stats-table">
                        <tr><td class="stats-label">Previous Close</td><td class="stats-value">{get_val('previousClose')}</td></tr>
                        <tr><td class="stats-label">Open</td><td class="stats-value">{get_val('open')}</td></tr>
                        <tr><td class="stats-label">Market Cap</td><td class="stats-value">{get_val('marketCap', "{:,.0f}")}</td></tr>
                        <tr><td class="stats-label">Beta (5Y Monthly)</td><td class="stats-value">{get_val('beta')}</td></tr>
                    </table>""", unsafe_allow_html=True)
                with s2:
                    st.markdown(f"""<table class="stats-table">
                        <tr><td class="stats-label">PE Ratio (TTM)</td><td class="stats-value">{get_val('trailingPE')}</td></tr>
                        <tr><td class="stats-label">EPS (TTM)</td><td class="stats-value">{get_val('trailingEps')}</td></tr>
                        <tr><td class="stats-label">Dividend Yield</td><td class="stats-value">{get_val('dividendYield', "{:.2%}")}</td></tr>
                        <tr><td class="stats-label">Ex-Dividend Date</td><td class="stats-value">{inf.get('exDividendDate', 'N/A')}</td></tr>
                    </table>""", unsafe_allow_html=True)

                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("🔥 Transition Risk Sensitivity")
                    risk_score = d['c_beta'] * 100 * tax_multiplier
                    fig_gauge = go.Figure(go.Indicator(mode = "gauge+number", value = risk_score,
                        gauge = {'axis': {'range': [-50, 50]}, 'bar': {'color': "white"},
                        'steps': [{'range': [-50, 0], 'color': '#238636'}, {'range': [0, 20], 'color': '#f1e05a'}, {'range': [20, 50], 'color': '#da3633'}]}))
                    fig_gauge.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=30, b=0))
                    st.plotly_chart(fig_gauge, use_container_width=True, key=f"g_{symbol}_{i}")
                    st.markdown(f'<div class="risk-card"><b>Insight:</b> ความเสี่ยงระดับ <b>{"High" if risk_score > 20 else "Low"}</b> ภายใต้ {scenario}</div>', unsafe_allow_html=True)

                with c2:
                    st.subheader("💰 Equity Value Bridge (MB)")
                    mkt_cap_mb = float(inf.get('marketCap', 1e11))/1e6
                    val_impact = (tax_price * 1000) / wacc / 1e6
                    fig_water = go.Figure(go.Waterfall(orientation = "v", measure = ["relative", "relative", "total"],
                        x = ["Initial Cap", "Climate Loss", "Adj. Value"], y = [mkt_cap_mb, -val_impact, mkt_cap_mb - val_impact],
                        text = [f"{mkt_cap_mb:,.0f}", f"-{val_impact:,.0f}", f"{(mkt_cap_mb-val_impact):,.0f}"], textposition = "outside",
                        increasing = {"marker":{"color":"#2ea043"}}, decreasing = {"marker":{"color":"#da3633"}}, totals = {"marker":{"color":"#1f6feb"}}))
                    fig_water.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=30, b=0))
                    st.plotly_chart(fig_water, use_container_width=True, key=f"w_{symbol}_{i}")
                    st.markdown(f'<div class="insight-card"><b>Insight:</b> มูลค่าปรับลด <b>-{val_impact:,.2f} MB</b> จาก Climate Risk</div>', unsafe_allow_html=True)

                st.divider()
                m1, m2 = st.columns([1.5, 1])
                with m1:
                    st.subheader("📈 Price Momentum")
                    st.line_chart(d['history'], height=250)
                with m2:
                    st.subheader("📰 Combined Insights")
                    if d['news']:
                        for n in d['news']:
                            st.write(f"**{n.get('publisher','Source')}**: {n.get('title','No Title')}")
                            st.divider()

# --- FOOTER ---
st.markdown("""<div class="footer">🏛️ Sustainable Finance Terminal | <b>Presented by Run Chantrapipat</b> | © 2026</div>""", unsafe_allow_html=True)
