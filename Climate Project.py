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

# --- CSS: ULTIMATE DARK TERMINAL UI (คงเดิมทุกประการ) ---
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
    div[data-testid="stMetricValue"] > div { 
        color: #00ff88 !important; 
        font-family: 'Inter', sans-serif;
        font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; gap: 10px; border: none; }
    .stTabs [data-baseweb="tab"] { 
        background-color: rgba(255, 255, 255, 0.05); 
        border-radius: 4px; padding: 10px 20px; color: #8b949e; border: none;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #2ea043 !important; 
        color: white !important; 
        font-weight: bold;
        box-shadow: 0 4px 12px rgba(46, 160, 67, 0.3);
    }
    .top-pick-container { border: 1px solid #2ea043; border-radius: 12px; padding: 15px; background: rgba(46, 160, 67, 0.08); box-shadow: 0 0 15px rgba(46, 160, 67, 0.15); margin-bottom: 25px; }
    .top-pick-title { color: #00ff88; font-weight: bold; font-size: 1.05rem; margin: 0; text-align: center; border-bottom: 1px solid rgba(46,160,67,0.3); padding-bottom: 10px; margin-bottom: 15px; }
    .top-pick-item { font-size: 0.88rem; font-weight: bold; margin-bottom: 12px; color: white; display: flex; justify-content: space-between; }
    .log-terminal { background: #000000 !important; border: 1px solid #2ea043 !important; border-radius: 8px; font-family: 'Courier New', Courier, monospace !important; padding: 15px; }
    .log-entry { color: #00ff88; font-size: 0.85rem; margin-bottom: 5px; }
    .stats-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
    .stats-table td { padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.9rem; color: white !important; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: rgba(13, 17, 23, 0.95); color: #8b949e; text-align: center; padding: 10px; font-size: 0.8rem; border-top: 1px solid rgba(255, 255, 255, 0.1); z-index: 999; }
    .block-container { padding-bottom: 100px; }
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
    stocks_html = "".join([f'<div class="top-pick-item"><span>{s["symbol"]}</span><span style="color:#8b949e; font-size:0.7rem;">Active Vol.</span></div>' for s in top_stocks])
    st.markdown(f'<div class="top-pick-container"><p class="top-pick-title">🌟 หุ้นเด่นวันนี้ (Real-time)</p>{stocks_html}</div>', unsafe_allow_html=True)

    with st.expander("🔍 Stock Selection", expanded=True):
        t1 = st.text_input("Stock 1", "PTT.BK")
        t2 = st.text_input("Stock 2", "EA.BK")
        t3 = st.text_input("Stock 3", "")
    
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

# --- DATA ENGINE (Maximum Reliability Version) ---
@st.cache_data(ttl=600)
def fetch_pro_data(ticker_list):
    full_res = {}
    
    # 1. โหลด Benchmark (ถ้าไม่ได้ไม่เป็นไร แค่ไม่มี Beta)
    proxies = pd.DataFrame()
    try:
        proxies = yf.download(["PTTEP.BK", "EA.BK", "^SET.BK"], period="1y", progress=False)['Close'].ffill()
    except: pass

    for symbol in ticker_list:
        try:
            t_obj = yf.Ticker(symbol)
            
            # 2. โหลดราคา (ต้องได้! ถ้าไม่ได้ตัวนี้จะถูกข้าม)
            hist = t_obj.history(period="1y")['Close'].ffill()
            if hist.empty: continue
            
            # 3. โหลด Info (ใส่ Try แยก เพื่อไม่ให้ Info พังแล้วอย่างอื่นพังตาม)
            info = {}
            try:
                info = t_obj.info
                if not info or 'regularMarketPrice' not in info: # บางครั้ง info มาเป็น None
                    info = {"shortName": symbol}
            except:
                info = {"shortName": symbol}

            # 4. โหลด News (ใส่ Try แยก)
            news = []
            try:
                news = t_obj.news[:3]
            except: pass

            # 5. คำนวณ Beta
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
                "news": news
            }
        except Exception as e:
            st.error(f"⚠️ Error loading {symbol}: {e}")
            continue
            
    return full_res

# --- MAIN DISPLAY ---
st.title("🏛️ CLIMATE RISK MODELING AND SUSTAINABLE FINANCE 🏛️")

if not tickers:
    st.info("💡 กรุณาระบุชื่อหุ้นใน Sidebar (เช่น PTT.BK) เพื่อเริ่มต้น")
else:
    analysis = fetch_pro_data(tickers)
    
    if not analysis:
        st.warning("❌ ไม่สามารถดึงข้อมูลหุ้นได้ โปรดตรวจสอบชื่อ Ticker (เช่น PTT.BK) หรือรีเฟรชหน้าเว็บ")
    else:
        # Overview Cards
        cols = st.columns(len(analysis))
        for i, (symbol, d) in enumerate(analysis.items()):
            cols[i].metric(f"💎 {symbol}", f"{d['price']:,.2f}", delta=f"C-Beta: {d['c_beta']:.3f}")

        # Intelligence Box Tabs
        tabs = st.tabs([f"Intelligence Center: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                # 1. กราฟราคา (ต้องขึ้น)
                st.subheader(f"📈 Price Performance: {symbol}")
                st.line_chart(d['history'], color="#00ff88")

                # 2. Market Summary
                st.subheader(f"📊 Market Summary: {symbol}")
                inf = d.get('info', {})
                s1, s2 = st.columns(2)
                
                def get_val(key, style="{:,.2f}", mult=1):
                    v = inf.get(key)
                    if v is None or v == 0: return "N/A"
                    try: return style.format(v * mult)
                    except: return str(v)

                with s1:
                    st.markdown(f'<table class="stats-table"><tr><td>Market Cap</td><td style="text-align:right">{get_val("marketCap", "{:,.0f}")}</td></tr><tr><td>Trailing P/E</td><td style="text-align:right">{get_val("trailingPE")}</td></tr><tr><td>Beta (5Y)</td><td style="text-align:right">{get_val("beta")}</td></tr></table>', unsafe_allow_html=True)
                with s2:
                    st.markdown(f'<table class="stats-table"><tr><td>Profit Margin</td><td style="text-align:right">{get_val("profitMargins", "{:.2%}")}</td></tr><tr><td>Dividend Yield</td><td style="text-align:right">{get_val("dividendYield", "{:.2%}")}</td></tr><tr><td>Debt/Equity</td><td style="text-align:right">{get_val("debtToEquity")}</td></tr></table>', unsafe_allow_html=True)

                st.divider()
                # 3. Risk Matrix
                st.subheader("🛡️ Comprehensive Climate Risk Matrix")
                de_ratio = inf.get('debtToEquity', 100) or 100
                dynamic_trans = d['c_beta'] * 100 * tax_multiplier
                credit_risk = "High" if (de_ratio > 150 or abs(dynamic_trans) > 25) else "Low"
                op_risk = "High" if flood_risk > 60 else "Low"
                
                r1, r2, r3, r4 = st.columns(4)
                r1.warning(f"💳 Credit: {credit_risk}")
                r2.error(f"🏗️ Operational: {op_risk}")
                r3.info(f"💧 Liquidity: Low")
                r4.success(f"⚖️ Liability: Low")

                st.divider()
                # 4. Gauge & Waterfall
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("🔥 Transition Risk Sensitivity")
                    fig_gauge = go.Figure(go.Indicator(mode = "gauge+number", value = dynamic_trans,
                        gauge = {'axis': {'range': [-50, 50]}, 'bar': {'color': "white"},
                        'steps': [{'range': [-50, 0], 'color': '#238636'}, {'range': [0, 20], 'color': '#f1e05a'}, {'range': [20, 50], 'color': '#da3633'}]}))
                    fig_gauge.update_layout(height=300, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=0, b=0))
                    st.plotly_chart(fig_gauge, use_container_width=True, key=f"gauge_{symbol}")
                
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
                    st.plotly_chart(fig_water, use_container_width=True, key=f"water_{symbol}")

                st.divider()
                # 5. News Feed
                st.subheader(f"📰 Intelligence Feed: {symbol}")
                if d['news']:
                    for n in d['news']:
                        st.markdown(f"**[{n.get('publisher', 'News')}]** {n.get('title')}")
                        st.caption(f"🔗 [Link]({n.get('link')})")
                else:
                    st.write("No recent news found.")

                with st.expander("📟 Terminal Log", expanded=False):
                    st.markdown(f'<div class="log-terminal"><div class="log-entry">[{datetime.now().strftime("%H:%M:%S")}] > SUCCESS: Data synchronized.</div></div>', unsafe_allow_html=True)

# --- FOOTER ---
st.markdown(f'<div class="footer">🏛️ Climate Risk Modeling and Sustainable Finance | <b>Presented by Run Chantrapipat</b> | © 2026</div>', unsafe_allow_html=True)
