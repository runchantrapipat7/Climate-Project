import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Climate Finance Pro Terminal", layout="wide")

# --- CSS: MODERN UI, GREEN TABS & DYNAMIC POP-UP ---
st.markdown("""
    <style>
    .main { background: radial-gradient(circle at top right, #1a1f2e, #0d1117); color: white; }
    .stTabs [data-baseweb="tab"] { background-color: rgba(255, 255, 255, 0.05); border-radius: 4px; padding: 10px 25px; color: #8b949e; border: none; }
    .stTabs [aria-selected="true"] { background-color: #2ea043 !important; color: white !important; font-weight: bold; }
    .top-pick-box { background: rgba(46, 160, 67, 0.1); border: 1px solid #2ea043; border-radius: 15px; padding: 15px; box-shadow: 0 0 20px rgba(46, 160, 67, 0.2); margin-bottom: 20px; }
    div[data-testid="stMetric"] { background: rgba(255, 255, 255, 0.03) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; border-radius: 12px; padding: 15px; }
    .insight-card { background: rgba(0, 255, 136, 0.05); border-left: 4px solid #00ff88; padding: 15px; border-radius: 8px; margin-top: 10px; font-size: 0.9rem; }
    .risk-card { background: rgba(255, 75, 75, 0.05); border-left: 4px solid #ff4b4b; padding: 15px; border-radius: 8px; margin-top: 10px; font-size: 0.9rem; }
    .stats-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
    .stats-table td { padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.9rem; }
    .stats-label { color: #8b949e; }
    .stats-value { text-align: right; font-weight: bold; color: #ffffff; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: rgba(13, 17, 23, 0.95); color: #8b949e; text-align: center; padding: 10px; font-size: 0.8rem; border-top: 1px solid rgba(255, 255, 255, 0.1); z-index: 999; }
    .block-container { padding-bottom: 80px; }
    </style>
    """, unsafe_allow_html=True)

# --- DYNAMIC TOP PICKS FROM YFINANCE ---
@st.cache_data(ttl=3600)
def get_real_top_picks():
    # ดึงข้อมูลหุ้นที่มี Volume สูงสุดเพื่อหาหุ้นเด่น
    tickers_to_watch = ["PTT.BK", "CPALL.BK", "AOT.BK", "EA.BK", "KBANK.BK", "ADVANC.BK"]
    picks = []
    for t in tickers_to_watch:
        try:
            d = yf.Ticker(t).history(period="1d")
            if not d.empty:
                picks.append({"symbol": t, "vol": d['Volume'].iloc[-1]})
        except: continue
    # เรียงลำดับตาม Volume และเลือก 2 อันดับแรก
    sorted_picks = sorted(picks, key=lambda x: x['vol'], reverse=True)[:2]
    return sorted_picks

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Risk Controller")
    with st.expander("🔍 ระบุชื่อหุ้นหรือกองทุน (Stock or Bond)", expanded=True):
        t1 = st.text_input("Asset 1", "PTT.BK")
        t2 = st.text_input("Asset 2", "EA.BK")
        t3 = st.text_input("Asset 3", "TPIPP.BK")
    
    st.divider()
    with st.expander("🌍 Scenario & Policy (TCFD)", expanded=True):
        scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
        tax_multiplier = {"Net Zero 2050": 1.5, "Delayed Transition": 1.0, "Current Policy": 0.5}[scenario]
        tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    st.divider()
    with st.expander("⚙️ Advanced Parameters", expanded=True):
        flood_risk = st.slider("Flood Exposure (%)", 0, 100, 45)
        wacc = st.slider("WACC (%)", 5.0, 15.0, 8.0) / 100

    # 💡 แก้ไข: หุ้นเด่นวันนี้ ดึงข้อมูลจริงจาก yfinance
    top_stocks = get_real_top_picks()
    st.markdown('<div class="top-pick-box"><h4 style="color: #00ff88; margin-top:0;">🌟 หุ้นเด่นวันนี้ (Real-time)</h4>', unsafe_allow_html=True)
    for stock in top_stocks:
        st.markdown(f'<p style="font-size: 0.85rem; margin-bottom: 5px;"><b>{stock["symbol"]}</b> (Active Volume)</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-size: 0.75rem; color: #8b949e;">อัปเดตข้อมูลจาก Yahoo Finance รายวัน</p></div>', unsafe_allow_html=True)

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
                st.subheader(f"📊 Market Summary: {symbol}")
                inf = d['info']
                s1, s2 = st.columns(2)
                def fmt(key, style="{:,.2f}"):
                    val = inf.get(key)
                    return style.format(val) if val is not None else "N/A"
                with s1:
                    st.markdown(f"""<table class="stats-table">
                        <tr><td class="stats-label">Market Cap</td><td class="stats-value">{fmt('marketCap', "{:,.0f}")}</td></tr>
                        <tr><td class="stats-label">Trailing P/E</td><td class="stats-value">{fmt('trailingPE')}</td></tr>
                        <tr><td class="stats-label">Beta (5Y Monthly)</td><td class="stats-value">{fmt('beta')}</td></tr>
                    </table>""", unsafe_allow_html=True)
                with s2:
                    st.markdown(f"""<table class="stats-table">
                        <tr><td class="stats-label">Profit Margin</td><td class="stats-value">{fmt('profitMargins', "{:.2%}")}</td></tr>
                        <tr><td class="stats-label">Dividend Yield</td><td class="stats-value">{fmt('dividendYield', "{:.2%}")}</td></tr>
                        <tr><td class="stats-label">Total Debt/Equity</td><td class="stats-value">{fmt('debtToEquity')}</td></tr>
                    </table>""", unsafe_allow_html=True)

                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("🔥 Transition Risk Sensitivity")
                    risk_score = d['c_beta'] * 100 * tax_multiplier
                    fig_gauge = go.Figure(go.Indicator(mode = "gauge+number", value = risk_score,
                        gauge = {'axis': {'range': [-50, 50]}, 'bar': {'color': "white"},
                        'steps': [{'range': [-50, 0], 'color': '#238636'}, {'range': [0, 20], 'color': '#f1e05a'}, {'range': [20, 50], 'color': '#da3633'}]}))
                    fig_gauge.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig_gauge, use_container_width=True, key=f"g_{symbol}_{i}")
                    st.markdown(f'<div class="risk-card"><b>Insight:</b> ความเสี่ยง C-Beta คือ <b>{risk_score:.2f}</b></div>', unsafe_allow_html=True)
                with c2:
                    st.subheader("💰 Equity Value Bridge (MB)")
                    mkt_cap_mb = float(inf.get('marketCap', 1e11))/1e6
                    val_impact = (tax_price * 1000) / wacc / 1e6
                    fig_water = go.Figure(go.Waterfall(orientation = "v", measure = ["relative", "relative", "total"],
                        x = ["Initial Cap", "Climate Loss", "Adj. Value"], y = [mkt_cap_mb, -val_impact, mkt_cap_mb - val_impact],
                        text = [f"{mkt_cap_mb:,.0f}", f"-{val_impact:,.0f}", f"{(mkt_cap_mb-val_impact):,.0f}"], textposition = "outside",
                        increasing = {"marker":{"color":"#2ea043"}}, decreasing = {"marker":{"color":"#da3633"}}, totals = {"marker":{"color":"#1f6feb"}}))
                    fig_water.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig_water, use_container_width=True, key=f"w_{symbol}_{i}")
                    st.markdown(f'<div class="insight-card"><b>Insight:</b> มูลค่าปรับลด <b>-{val_impact:,.2f} MB</b></div>', unsafe_allow_html=True)
                st.divider()
                m1, m2 = st.columns([1.5, 1])
                with m1:
                    st.subheader("📈 Price Momentum")
                    st.line_chart(d['history'], height=250)
                with m2:
                    st.subheader("📰 Combined Insights")
                    if d['news']:
                        for n in d['news']:
                            st.write(f"**{n.get('publisher','Source')}**: {n.get('title','Latest Update')}")
                            st.divider()

# --- FOOTER ---
st.markdown(f"""<div class="footer">🏛️ Sustainable Finance Terminal | <b>Presented by Run Chantrapipat</b> | © 2026</div>""", unsafe_allow_html=True)
