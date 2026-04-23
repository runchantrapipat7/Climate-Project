import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Climate Finance Pro Terminal", layout="wide")

# --- CSS: ULTIMATE DARK TERMINAL UI (คงเดิมและปรับปรุงตาราง) ---
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
    .stats-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
    .stats-table td { padding: 12px 8px; border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 0.95rem; color: white; }
    .academic-label { color: #8b949e; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; }
    .impact-positive { color: #00ff88; font-weight: bold; }
    .impact-negative { color: #ff4b4b; font-weight: bold; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: rgba(13, 17, 23, 0.95); text-align: center; padding: 10px; font-size: 0.8rem; border-top: 1px solid rgba(255, 255, 255, 0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- TOP PICKS ENGINE ---
@st.cache_data(ttl=3600)
def get_real_top_picks_5():
    candidate_tickers = ["PTT.BK", "CPALL.BK", "AOT.BK", "KBANK.BK", "EA.BK", "ADVANC.BK", "GULF.BK", "SCB.BK"]
    picks = []
    try:
        data = yf.download(candidate_tickers, period="5d", progress=False)['Volume']
        for t in candidate_tickers:
            if t in data.columns:
                v = data[t].dropna()
                if not v.empty: picks.append({"symbol": t, "volume": v.iloc[-1]})
    except: pass
    return sorted(picks, key=lambda x: x['volume'], reverse=True)[:5]

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Risk Controller")
    top_stocks = get_real_top_picks_5()
    stocks_html = "".join([f'<div style="display:flex; justify-content:space-between; margin-bottom:10px;"><span>{s["symbol"]}</span><span style="color:#00ff88;">Active</span></div>' for s in top_stocks])
    st.markdown(f'<div style="border:1px solid #2ea043; padding:15px; border-radius:12px; background:rgba(46,160,67,0.1);">{stocks_html}</div>', unsafe_allow_html=True)

    t1 = st.text_input("Asset 1", "PTT.BK")
    t2 = st.text_input("Asset 2", "EA.BK")
    
    st.divider()
    scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
    tax_multiplier = {"Net Zero 2050": 1.5, "Delayed Transition": 1.0, "Current Policy": 0.5}[scenario]
    tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    flood_risk = st.slider("Flood Exposure (%)", 0, 100, 35)
    wacc = st.slider("WACC (%)", 5.0, 20.0, 12.0) / 100

    tickers = [t.strip().upper() for t in [t1, t2] if t.strip()]

# --- DATA ENGINE ---
@st.cache_data(ttl=600)
def fetch_pro_data(ticker_list):
    full_res = {}
    proxies = pd.DataFrame()
    try:
        proxies = yf.download(["PTTEP.BK", "EA.BK", "^SET.BK"], period="1y", progress=False)['Close'].ffill()
    except: pass

    for symbol in ticker_list:
        try:
            t_obj = yf.Ticker(symbol)
            hist = t_obj.history(period="1y")['Close'].ffill()
            if hist.empty: continue
            
            info = t_obj.info if t_obj.info else {}
            # Fallback for Market Cap
            if not info.get('marketCap'):
                fast = t_obj.fast_info
                info['marketCap'] = fast.get('market_cap', 0)

            c_beta = 0.0
            if not proxies.empty:
                try:
                    combined = pd.concat([hist.pct_change(), proxies.pct_change()], axis=1).dropna()
                    combined.columns = ['target', 'pttep', 'ea', 'set']
                    bmg = combined['pttep'] - combined['ea']
                    X = sm.add_constant(pd.DataFrame({'Market': combined['set'], 'Carbon': bmg}))
                    c_beta = sm.OLS(combined['target'], X).fit().params.get('Carbon', 0.0)
                except: pass

            full_res[symbol] = {
                "price": float(hist.iloc[-1]),
                "history": hist,
                "c_beta": c_beta,
                "info": info,
                "news": t_obj.news[:3] if t_obj.news else []
            }
        except: continue
    return full_res

# --- MAIN DISPLAY ---
st.title("🏛️ SUSTAINABLE FINANCE ASSET TERMINAL")

if not tickers:
    st.info("💡 กรุณาระบุชื่อหุ้นเพื่อเริ่มต้น")
else:
    analysis = fetch_pro_data(tickers)
    
    if analysis:
        cols = st.columns(len(analysis))
        for i, (symbol, d) in enumerate(analysis.items()):
            cols[i].metric(f"💎 {symbol}", f"{d['price']:,.2f}", delta=f"C-Beta: {d['c_beta']:.3f}")

        tabs = st.tabs([f"Analysis: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                # 1. Price Chart
                st.subheader("📈 Historical Performance")
                st.line_chart(d['history'], color="#00ff88")

                # 2. Academic Market & Climate Summary
                st.subheader("🔬 Financial & Climate-Adjusted Metrics")
                inf = d.get('info', {})
                
                # --- การคำนวณเชิงวิชาการเพิ่มเติม ---
                mkt_cap = inf.get('marketCap', 0) or 0
                carbon_impact_pct = d['c_beta'] * tax_multiplier * 100 # % impact on price
                
                # จำลองการคำนวณ Adjusted PE
                raw_pe = inf.get('trailingPE', 0) or 0
                adj_pe = raw_pe * (1 + (abs(carbon_impact_pct)/100)) if raw_pe else 0

                s1, s2 = st.columns(2)
                with s1:
                    st.markdown(f"""
                    <table class="stats-table">
                        <tr><td><span class="academic-label">Market Capitalization</span></td><td style="text-align:right">฿{mkt_cap:,.0f}</td></tr>
                        <tr><td><span class="academic-label">Trailing P/E (Standard)</span></td><td style="text-align:right">{raw_pe if raw_pe else 'N/A'}</td></tr>
                        <tr><td><span class="academic-label">Climate-Adjusted P/E</span></td><td style="text-align:right; color:#00ff88;">{adj_pe:.2f}</td></tr>
                    </table>
                    """, unsafe_allow_html=True)
                
                with s2:
                    impact_class = "impact-negative" if carbon_impact_pct > 0 else "impact-positive"
                    st.markdown(f"""
                    <table class="stats-table">
                        <tr><td><span class="academic-label">Carbon Sensitivity Index</span></td><td style="text-align:right">{d['c_beta']:.4f}</td></tr>
                        <tr><td><span class="academic-label">Estimated Price Volatility</span></td><td style="text-align:right">±{abs(carbon_impact_pct):.2f}%</td></tr>
                        <tr><td><span class="academic-label">TCFD Scenario Impact</span></td><td style="text-align:right" class="{impact_class}">{carbon_impact_pct:+.2f}%</td></tr>
                    </table>
                    """, unsafe_allow_html=True)

                st.divider()
                # 3. Risk Matrix
                st.subheader("🛡️ Risk Exposure Framework")
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("Transition Risk", f"{abs(carbon_impact_pct):.1f}%", "Sensitivity")
                r2.metric("Physical Risk", f"{flood_risk}%", "Exposure")
                r3.metric("Regulatory Risk", scenario, "Policy")
                r4.metric("Cost of Capital", f"{wacc*100:.1f}%", "WACC")

                st.divider()
                # 4. Charts
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("🔥 Carbon Sensitivity Gauge")
                    dynamic_trans = d['c_beta'] * 100 * tax_multiplier
                    fig_gauge = go.Figure(go.Indicator(mode = "gauge+number", value = dynamic_trans,
                        title = {'text': "Impact %", 'font': {'size': 14}},
                        gauge = {'axis': {'range': [-50, 50]}, 'bar': {'color': "white"},
                        'steps': [{'range': [-50, 0], 'color': '#238636'}, {'range': [0, 20], 'color': '#f1e05a'}, {'range': [20, 50], 'color': '#da3633'}]}))
                    fig_gauge.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=30, b=0))
                    st.plotly_chart(fig_gauge, use_container_width=True)
                
                with c2:
                    st.subheader("💰 Valuation Bridge (Climate Loss)")
                    mkt_cap_mb = mkt_cap / 1e6
                    val_impact = (tax_price * 1000 * abs(d['c_beta'])) / wacc / 1e6
                    adj_val = mkt_cap_mb - val_impact
                    fig_water = go.Figure(go.Waterfall(orientation = "v", measure = ["relative", "relative", "total"],
                        x = ["Current Cap", "Climate Loss", "Adj. Valuation"], y = [mkt_cap_mb, -val_impact, adj_val],
                        increasing = {"marker":{"color":"#2ea043"}}, decreasing = {"marker":{"color":"#da3633"}}, totals = {"marker":{"color":"#1f6feb"}}))
                    fig_water.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=30, b=0))
                    st.plotly_chart(fig_water, use_container_width=True)

                # 5. News
                st.subheader("📰 Intelligence Feed")
                if d['news']:
                    for n in d['news']:
                        st.markdown(f"**[{n.get('publisher', 'News')}]** {n.get('title')}")
                        st.caption(f"🔗 [Link]({n.get('link')})")

st.markdown(f'<div class="footer">🏛️ Sustainable Finance Terminal | © 2026</div>', unsafe_allow_html=True)
