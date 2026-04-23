import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Climate Finance Pro Terminal", layout="wide")

# --- CSS: ULTIMATE DARK TERMINAL UI (คงเดิมและเสริมสไตล์วิชาการ) ---
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
    .stats-table td { padding: 12px 8px; border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 0.95rem; color: white !important; }
    .academic-header { color: #00ff88; font-size: 1.1rem; font-weight: bold; margin-bottom: 15px; border-left: 4px solid #2ea043; padding-left: 10px; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: rgba(13, 17, 23, 0.95); text-align: center; padding: 10px; font-size: 0.8rem; border-top: 1px solid rgba(255, 255, 255, 0.1); z-index: 999;}
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

# --- SIDEBAR (คืนค่า Asset 3 และพารามิเตอร์ทั้งหมด) ---
with st.sidebar:
    st.title("🛡️ Risk Controller")
    top_stocks = get_real_top_picks_5()
    stocks_html = "".join([f'<div style="display:flex; justify-content:space-between; margin-bottom:10px;"><span>{s["symbol"]}</span><span style="color:#00ff88; font-size:0.7rem;">Active Vol.</span></div>' for s in top_stocks])
    st.markdown(f'<div style="border:1px solid #2ea043; padding:15px; border-radius:12px; background:rgba(46,160,67,0.08);">{stocks_html}</div>', unsafe_allow_html=True)

    with st.expander("🔍 Asset Selection", expanded=True):
        t1 = st.text_input("Asset 1", "PTT.BK")
        t2 = st.text_input("Asset 2", "EA.BK")
        t3 = st.text_input("Asset 3", "") # คืนค่า Asset 3
    
    st.divider()
    with st.expander("🌍 Scenario Policy (TCFD)", expanded=True):
        scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
        tax_multiplier = {"Net Zero 2050": 1.5, "Delayed Transition": 1.0, "Current Policy": 0.5}[scenario]
        tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    with st.expander("⚙️ Physical Risk Parameters", expanded=True):
        flood_risk = st.slider("Flood Exposure (%)", 0, 100, 35)
        wacc = st.slider("WACC (%)", 5.0, 20.0, 12.0) / 100

    tickers = [t.strip().upper() for t in [t1, t2, t3] if t.strip()]

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
            if not info.get('marketCap'):
                info['marketCap'] = t_obj.fast_info.get('market_cap', 0)

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
    st.info("💡 กรุณาระบุชื่อหุ้นใน Sidebar เพื่อเริ่มต้นการวิเคราะห์")
else:
    analysis = fetch_pro_data(tickers)
    if analysis:
        cols = st.columns(len(analysis))
        for i, (symbol, d) in enumerate(analysis.items()):
            cols[i].metric(f"💎 {symbol}", f"{d['price']:,.2f}", delta=f"C-Beta: {d['c_beta']:.3f}")

        tabs = st.tabs([f"Intelligence Center: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                # กราฟราคา
                st.subheader(f"📈 Price Performance: {symbol}")
                st.line_chart(d['history'], color="#00ff88")

                # --- ส่วนของ Market Summary (คืนค่าทุกตัวและเพิ่ม % วิเคราะห์) ---
                st.markdown(f'<div class="academic-header">📊 Market Summary & Climate Analysis: {symbol}</div>', unsafe_allow_html=True)
                inf = d.get('info', {})
                
                # คำนวณ % Impact เชิงวิชาการ
                carbon_impact_pct = d['c_beta'] * tax_multiplier * 100
                raw_pe = inf.get('trailingPE', 0) or 0
                adj_pe = raw_pe * (1 + (abs(carbon_impact_pct)/100)) if raw_pe else 0

                s1, s2 = st.columns(2)
                
                def get_val(key, style="{:,.2f}", mult=1):
                    v = inf.get(key)
                    if v is None or v == 0: return "N/A"
                    try: return style.format(float(v) * mult)
                    except: return str(v)

                with s1:
                    st.markdown(f"""
                    <table class="stats-table">
                        <tr><td>Market Cap</td><td style="text-align:right"><b>฿{get_val('marketCap', '{:,.0f}')}</b></td></tr>
                        <tr><td>Trailing P/E</td><td style="text-align:right"><b>{get_val('trailingPE')}</b></td></tr>
                        <tr><td>Beta (5Y)</td><td style="text-align:right"><b>{get_val('beta')}</b></td></tr>
                        <tr style="background:rgba(0,255,136,0.05);"><td>Climate-Adj. P/E (Est.)</td><td style="text-align:right; color:#00ff88;"><b>{adj_pe:.2f}</b></td></tr>
                    </table>
                    """, unsafe_allow_html=True)
                
                with s2:
                    st.markdown(f"""
                    <table class="stats-table">
                        <tr><td>Profit Margin</td><td style="text-align:right"><b>{get_val('profitMargins', '{:.2%}')}</b></td></tr>
                        <tr><td>Dividend Yield</td><td style="text-align:right"><b>{get_val('dividendYield', '{:.2%}')}</b></td></tr>
                        <tr><td>Debt/Equity</td><td style="text-align:right"><b>{get_val('debtToEquity')}</b></td></tr>
                        <tr style="background:rgba(255,75,75,0.05);"><td>Policy Sensitivity (%)</td><td style="text-align:right; color:#ff4b4b;"><b>{carbon_impact_pct:+.2f}%</b></td></tr>
                    </table>
                    """, unsafe_allow_html=True)

                st.divider()
                # Risk Matrix
                st.subheader("🛡️ Comprehensive Climate Risk Matrix")
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("Transition Risk", f"{abs(carbon_impact_pct):.1f}%", "Impact")
                r2.metric("Physical Risk", f"{flood_risk}%", "Flood")
                r3.metric("Regulatory Risk", "High" if tax_multiplier > 1 else "Medium", scenario)
                r4.metric("Cost of Capital", f"{wacc*100:.1f}%", "WACC")

                st.divider()
                # Gauge & Waterfall
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("🔥 Transition Risk Sensitivity")
                    fig_gauge = go.Figure(go.Indicator(mode = "gauge+number", value = carbon_impact_pct,
                        gauge = {'axis': {'range': [-50, 50]}, 'bar': {'color': "white"},
                        'steps': [{'range': [-50, 0], 'color': '#238636'}, {'range': [0, 20], 'color': '#f1e05a'}, {'range': [20, 50], 'color': '#da3633'}]}))
                    fig_gauge.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=0, b=0))
                    st.plotly_chart(fig_gauge, use_container_width=True, key=f"g_{symbol}")
                
                with c2:
                    st.subheader("💰 Equity Value Bridge (MB)")
                    mkt_cap_mb = (inf.get('marketCap', 1e11) or 1e11) / 1e6
                    val_impact = (tax_price * 1000 * abs(d['c_beta'])) / wacc / 1e6
                    adj_val = mkt_cap_mb - val_impact
                    fig_water = go.Figure(go.Waterfall(orientation = "v", measure = ["relative", "relative", "total"],
                        x = ["Initial Cap", "Climate Loss", "Adj. Value"], y = [mkt_cap_mb, -val_impact, adj_val],
                        text = [f"{mkt_cap_mb:,.0f}", f"-{val_impact:,.0f}", f"{adj_val:,.0f}"], textposition = "outside",
                        increasing = {"marker":{"color":"#2ea043"}}, decreasing = {"marker":{"color":"#da3633"}}, totals = {"marker":{"color":"#1f6feb"}}))
                    fig_water.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=0, b=0))
                    st.plotly_chart(fig_water, use_container_width=True, key=f"w_{symbol}")

                st.divider()
                # --- คืนค่า News Feed ---
                st.subheader(f"📰 Intelligence Feed: {symbol}")
                if d['news']:
                    for n in d['news']:
                        st.markdown(f"**[{n.get('publisher', 'News')}]** {n.get('title')}")
                        st.caption(f"🔗 [Link]({n.get('link')})")
                else:
                    st.write("No recent news found.")

# --- FOOTER ---
st.markdown(f'<div class="footer">🏛️ Sustainable Finance Terminal | <b>Presented by Run Chantrapipat</b> | © 2026</div>', unsafe_allow_html=True)
