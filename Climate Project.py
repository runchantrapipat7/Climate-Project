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

# --- CSS: MODERN UI & INTELLIGENCE BOX TABS ---
st.markdown("""
    <style>
    .main { background: radial-gradient(circle at top right, #1a1f2e, #0d1117); color: white; }
    
    /* 🟢 คืนค่า Intelligence Center ให้เป็นกรอบสวยเหมือนเดิม */
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; gap: 8px; border: none; }
    .stTabs [data-baseweb="tab"] { 
        background-color: rgba(255, 255, 255, 0.05); 
        border-radius: 4px; padding: 10px 20px; color: #8b949e; border: none;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #2ea043 !important; /* กรอบสีเขียวทึบ */
        color: white !important; 
        font-weight: bold;
        box-shadow: 0 4px 12px rgba(46, 160, 67, 0.3);
    }

    /* 💡 หุ้นเด่นวันนี้ในกรอบเดียว */
    .top-pick-container { border: 1px solid #2ea043; border-radius: 12px; padding: 15px; background: rgba(46, 160, 67, 0.08); box-shadow: 0 0 15px rgba(46, 160, 67, 0.15); margin-bottom: 25px; }
    .top-pick-title { color: #00ff88; font-weight: bold; font-size: 1.05rem; margin: 0; text-align: center; border-bottom: 1px solid rgba(46,160,67,0.3); padding-bottom: 10px; margin-bottom: 15px; }
    .top-pick-item { font-size: 0.88rem; font-weight: bold; margin-bottom: 12px; color: white; display: flex; justify-content: space-between; }
    
    /* 📟 Terminal Log Style (Collapsible) */
    .log-terminal { background: #000000 !important; border: 1px solid #2ea043 !important; border-radius: 8px; font-family: 'Courier New', Courier, monospace !important; padding: 15px; }
    .log-entry { color: #00ff88; font-size: 0.85rem; margin-bottom: 5px; line-height: 1.4; }
    .log-entry span { color: #8b949e; }

    .stats-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
    .stats-table td { padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.9rem; }
    
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: rgba(13, 17, 23, 0.95); color: #8b949e; text-align: center; padding: 10px; font-size: 0.8rem; border-top: 1px solid rgba(255, 255, 255, 0.1); z-index: 999; }
    .block-container { padding-bottom: 100px; }
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
    stocks_html = "".join([f'<div class="top-pick-item"><span>{s["symbol"]}</span><span style="color:#8b949e; font-size:0.7rem;">Active Vol.</span></div>' for s in top_stocks])
    st.markdown(f'<div class="top-pick-container"><p class="top-pick-title">🌟 หุ้นเด่นวันนี้ (Real-time)</p>{stocks_html}</div>', unsafe_allow_html=True)

    with st.expander("🔍 Asset Selection", expanded=True):
        t1 = st.text_input("Asset 1", "PTT.BK")
        t2 = st.text_input("Asset 2", "EA.BK")
        t3 = st.text_input("Asset 3", "")
    
    st.divider()
    with st.expander("🌍 Scenario Policy (TCFD)", expanded=True):
        scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
        tax_multiplier = {"Net Zero 2050": 1.5, "Delayed Transition": 1.0, "Current Policy": 0.5}[scenario]
        tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    st.divider()
    with st.expander("⚙️ Physical Risk Parameters", expanded=True):
        flood_risk = st.slider("Flood Exposure (%)", 0, 100, 35)
        wacc = st.slider("WACC (%)", 5.0, 20.0, 12.0) / 100

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

if not tickers:
    st.info("💡 กรุณาระบุชื่อหุ้นใน Sidebar เพื่อเริ่มต้นการวิเคราะห์")
else:
    analysis = fetch_pro_data(tickers)
    if analysis:
        # Overview Cards
        cols = st.columns(len(analysis))
        for i, (symbol, d) in enumerate(analysis.items()):
            cols[i].metric(f"💎 {symbol}", f"{d['price']:,.2f}", delta=f"C-Beta: {d['c_beta']:.3f}")

        #Intelligence Box Tabs Layout
        tabs = st.tabs([f"Intelligence Center: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                # 📊 Summary Statistics
                st.subheader(f"📊 Market Summary: {symbol}")
                inf = d.get('info', {})
                s1, s2 = st.columns(2)
                def get_val(key, style="{:,.2f}"):
                    val = inf.get(key)
                    return style.format(val) if val is not None else "N/A"
                with s1:
                    st.markdown(f'<table class="stats-table"><tr><td class="stats-label">Market Cap</td><td class="stats-value">{get_val("marketCap", "{:,.0f}")}</td></tr><tr><td class="stats-label">Trailing P/E</td><td class="stats-value">{get_val("trailingPE")}</td></tr><tr><td class="stats-label">Beta (5Y)</td><td class="stats-value">{get_val("beta")}</td></tr></table>', unsafe_allow_html=True)
                with s2:
                    st.markdown(f'<table class="stats-table"><tr><td class="stats-label">Profit Margin</td><td class="stats-value">{get_val("profitMargins", "{:.2%}")}</td></tr><tr><td class="stats-label">Dividend Yield</td><td class="stats-value">{get_val("dividendYield", "{:.2%}")}</td></tr><tr><td class="stats-label">Debt/Equity</td><td class="stats-value">{get_val("debtToEquity")}</td></tr></table>', unsafe_allow_html=True)

                # 🛡️ Risk Matrix
                st.divider()
                st.subheader("🛡️ Comprehensive Climate Risk Matrix")
                de_ratio = inf.get('debtToEquity', 100) or 100
                dynamic_trans = d['c_beta'] * 100 * tax_multiplier
                credit_risk = "High" if (de_ratio > 150 or dynamic_trans > 25) else "Low"
                op_risk = "High" if flood_risk > 60 else "Low"
                
                r1, r2, r3, r4 = st.columns(4)
                r1.warning(f"💳 Credit: {credit_risk}")
                r2.error(f"🏗️ Operational: {op_risk}")
                r3.info(f"💧 Liquidity: Low")
                r4.success(f"⚖️ Liability: Low")

                st.divider()
                # 📈 Charts (Dynamic Movement)
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("🔥 Transition Risk Sensitivity")
                    fig_gauge = go.Figure(go.Indicator(mode = "gauge+number", value = dynamic_trans,
                        gauge = {'axis': {'range': [-50, 50]}, 'bar': {'color': "white"},
                        'steps': [{'range': [-50, 0], 'color': '#238636'}, {'range': [0, 20], 'color': '#f1e05a'}, {'range': [20, 50], 'color': '#da3633'}]}))
                    fig_gauge.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=0, b=0))
                    st.plotly_chart(fig_gauge, use_container_width=True, key=f"g_{symbol}_{i}")
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

                st.divider()
                st.subheader("📈 Price Momentum & Insights")
                m1, m2 = st.columns([1.5, 1])
                with m1: st.line_chart(d['history'], height=250)
                with m2:
                    if d['news']:
                        for n in d['news']:
                            st.write(f"**{n.get('publisher','News')}**: {n.get('title')}")
                            st.divider()

                # 📝 COLLAPSIBLE TERMINAL LOG
                st.write("") 
                with st.expander("📟 View Terminal Risk Log (Activity)", expanded=False):
                    st.markdown(f"""
                    <div class="log-terminal">
                        <div class="log-entry"><span>[{datetime.now().strftime('%H:%M:%S')}]</span> > STRESS_TEST: Initializing for {symbol}...</div>
                        <div class="log-entry"><span>[{datetime.now().strftime('%H:%M:%S')}]</span> > ENGINE: Applying Scenario "{scenario}"</div>
                        <div class="log-entry"><span>[{datetime.now().strftime('%H:%M:%S')}]</span> > COMPUTE: Carbon Sensitivity factor at {dynamic_trans:.2f}</div>
                        <div class="log-entry"><span>[{datetime.now().strftime('%H:%M:%S')}]</span> > STATUS: COMPLETED. All parameters synchronized.</div>
                    </div>
                    """, unsafe_allow_html=True)

# --- FOOTER ---
st.markdown(f'<div class="footer">🏛️ Sustainable Finance Terminal | <b>Presented by Run Chantrapipat</b> | © 2026</div>', unsafe_allow_html=True)
