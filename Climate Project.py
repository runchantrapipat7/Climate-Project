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

# --- CSS: ULTIMATE DARK TERMINAL UI (คงเดิมจากไฟล์ต้นฉบับ 100%) ---
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
    .top-pick-container { border: 1px solid #2ea043; border-radius: 12px; padding: 15px; background: rgba(46,160,67,0.08); margin-bottom: 25px; }
    .top-pick-title { color: #00ff88; font-weight: bold; font-size: 1.05rem; text-align: center; border-bottom: 1px solid rgba(46,160,67,0.3); padding-bottom: 10px; margin-bottom: 15px; }
    .top-pick-item { font-size: 0.88rem; font-weight: bold; margin-bottom: 12px; color: white; display: flex; justify-content: space-between; }
    .log-terminal { background: #000000 !important; border: 1px solid #2ea043 !important; border-radius: 8px; font-family: 'Courier New', Courier, monospace !important; padding: 15px; }
    .log-entry { color: #00ff88; font-size: 0.85rem; margin-bottom: 5px; }
    .academic-box { background: rgba(0, 255, 136, 0.03); border: 1px dashed rgba(0, 255, 136, 0.3); border-radius: 10px; padding: 20px; margin-top: 10px; }
    .academic-label { color: #00ff88; font-size: 0.8rem; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
    .market-card { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(0, 255, 136, 0.1); border-radius: 12px; padding: 18px; margin-bottom: 10px; text-align: center; }
    .market-label { color: #8b949e; font-size: 0.72rem; text-transform: uppercase; margin-bottom: 8px; }
    .market-value { color: #ffffff; font-size: 1.15rem; font-weight: 600; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: rgba(13, 17, 23, 0.95); color: #8b949e; text-align: center; padding: 10px; font-size: 0.8rem; border-top: 1px solid rgba(255, 255, 255, 0.1); z-index: 999; }
    </style>
    """, unsafe_allow_html=True)

# --- DATA ENGINE (รองรับทั้ง TH และ Global) ---
@st.cache_data(ttl=600)
def fetch_terminal_data(ticker_list, market_mode="TH"):
    full_res = {}
    proxies = pd.DataFrame()
    ref_idx = "^SET.BK" if market_mode == "TH" else "^GSPC"
    try:
        proxies = yf.download(["PTTEP.BK", "EA.BK", ref_idx], period="1y", progress=False)['Close'].ffill()
    except: pass

    for symbol in ticker_list:
        try:
            t_obj = yf.Ticker(symbol)
            hist = t_obj.history(period="2y")['Close'].ffill() 
            if hist.empty: continue
            
            info = t_obj.info if t_obj.info else {}
            news = t_obj.news[:5] if hasattr(t_obj, 'news') else []

            c_beta = 0.0
            if not proxies.empty and market_mode == "TH":
                try:
                    combined = pd.concat([hist.pct_change(), proxies.pct_change()], axis=1).dropna()
                    combined.columns = ['target', 'pttep', 'ea', 'market']
                    bmg = combined['pttep'] - combined['ea']
                    X = sm.add_constant(pd.DataFrame({'Market': combined['market'], 'Carbon': bmg}))
                    c_beta = sm.OLS(combined['target'], X).fit().params.get('Carbon', 0.0)
                except: pass

            full_res[symbol] = {"price": float(hist.iloc[-1]), "history": hist, "c_beta": c_beta, "info": info, "news": news}
        except: continue
    return full_res

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("🛡️ Risk Controller")
    app_mode = st.radio("Terminal Module", ["🇹🇭 Thai Climate Risk", "📈 Thai Trading Analysis", "🌎 Global Market Analysis"])
    st.divider()

# ==========================================
# MODULE 1: THAI CLIMATE RISK (โปรเจกต์เดิมของคุณครบถ้วน)
# ==========================================
if app_mode == "🇹🇭 Thai Climate Risk":
    with st.sidebar:
        with st.expander("🔍 Thai Stock Selection", expanded=True):
            t1 = st.text_input("Stock 1", "PTT.BK")
            t2 = st.text_input("Stock 2", "GULF.BK")
            tickers = [t.strip().upper() for t in [t1, t2] if t.strip()]
        
        with st.expander("🌍 Scenario Policy (TCFD)", expanded=True):
            scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
            tax_multiplier = {"Net Zero 2050": 1.5, "Delayed Transition": 1.0, "Current Policy": 0.5}[scenario]
            tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
            flood_risk = st.slider("Flood Exposure (%)", 0, 100, 35)
            wacc = st.slider("WACC (%)", 5.0, 20.0, 12.0) / 100

    st.title("🏛️ THAI CLIMATE RISK & SUSTAINABLE FINANCE")
    data = fetch_terminal_data(tickers, "TH")
    
    if data:
        tabs = st.tabs([f"Intelligence: {s}" for s in data.keys()])
        for i, (symbol, d) in enumerate(data.items()):
            with tabs[i]:
                # 1. Top Metrics
                m1, m2, m3, m4 = st.columns(4)
                curr_p = d['price']
                m1.metric("Current Price", f"฿{curr_p:,.2f}")
                m2.metric("Climate Beta", f"{d['c_beta']:.4f}")
                m3.metric("Market Cap", f"{d.get('info', {}).get('marketCap', 0)/1e9:.2f}B")
                m4.metric("TCFD Status", "STABLE" if abs(d['c_beta']) < 0.2 else "SENSITIVE")

                st.subheader(f"📈 Performance: {symbol}")
                st.line_chart(d['history'].iloc[-252:], color="#00ff88")

                # 2. Market Card Grid (จากไฟล์ต้นฉบับ)
                inf = d.get('info', {})
                def get_val(key, style="{:,.2f}"):
                    v = inf.get(key)
                    return style.format(float(v)) if v else "N/A"

                st.subheader("📊 Market Intelligence Grid")
                mc1, mc2, mc3 = st.columns(3); mc4, mc5, mc6 = st.columns(3)
                with mc1: st.markdown(f'<div class="market-card"><div class="market-label">P/E Ratio</div><div class="market-value">{get_val("trailingPE")}</div></div>', unsafe_allow_html=True)
                with mc2: st.markdown(f'<div class="market-card"><div class="market-label">P/B Ratio</div><div class="market-value">{get_val("priceToBook")}</div></div>', unsafe_allow_html=True)
                with mc3: st.markdown(f'<div class="market-card"><div class="market-label">Div. Yield</div><div class="market-value">{get_val("dividendYield", "{:.2%}")}</div></div>', unsafe_allow_html=True)
                with mc4: st.markdown(f'<div class="market-card"><div class="market-label">Beta (5Y)</div><div class="market-value">{get_val("beta")}</div></div>', unsafe_allow_html=True)
                with mc5: st.markdown(f'<div class="market-card"><div class="market-label">Profit Margin</div><div class="market-value">{get_val("profitMargins", "{:.2%}")}</div></div>', unsafe_allow_html=True)
                with mc6: st.markdown(f'<div class="market-card"><div class="market-label">Debt/Equity</div><div class="market-value">{get_val("debtToEquity")}</div></div>', unsafe_allow_html=True)

                # 3. Climate Quantitative Box (TCFD)
                st.markdown('<div class="academic-box">', unsafe_allow_html=True)
                st.markdown('<p class="academic-label">🔬 Quantitative Climate Analytics (TCFD)</p>', unsafe_allow_html=True)
                q1, q2, q3 = st.columns(3)
                dynamic_trans = d['c_beta'] * 100 * tax_multiplier
                climate_var = abs(dynamic_trans) * 0.1
                with q1: st.write(f"📊 **Sensitivity:** **{d['c_beta']:.4f}**")
                with q2: st.write(f"📉 **Climate VaR:** <span style='color:#ff4b4b;'>**{climate_var:,.2f}%**</span>", unsafe_allow_html=True)
                with q3: st.write(f"🏢 **Sector Risk:** {'High' if abs(d['c_beta']) > 0.3 else 'Low'}")
                st.markdown('</div>', unsafe_allow_html=True)

                # 4. Gauge & Waterfall
                c1, c2 = st.columns(2)
                with c1:
                    fig_g = go.Figure(go.Indicator(mode="gauge+number", value=dynamic_trans, title={'text': "Transition Sensitivity"}, gauge={'axis': {'range': [-50, 50]}, 'bar': {'color': "white"}, 'steps': [{'range': [-50, 0], 'color': '#238636'}, {'range': [0, 20], 'color': '#f1e05a'}, {'range': [20, 50], 'color': '#da3633'}]}))
                    fig_g.update_layout(height=280, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig_g, use_container_width=True, key=f"gauge_{symbol}")
                with c2:
                    raw_cap = inf.get('marketCap', 1e9); mkt_cap_mb = float(raw_cap)/1e6
                    val_impact = (tax_price * 1000) / wacc / 1e6; adj_val = mkt_cap_mb - val_impact
                    fig_w = go.Figure(go.Waterfall(orientation="v", x=["Initial", "Climate Loss", "Adjusted"], y=[mkt_cap_mb, -val_impact, adj_val], textposition="outside", increasing={"marker":{"color":"#2ea043"}}, decreasing={"marker":{"color":"#da3633"}}, totals={"marker":{"color":"#1f6feb"}}))
                    fig_w.update_layout(height=280, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig_w, use_container_width=True, key=f"water_{symbol}")

                # 5. News & Log
                st.subheader("📰 Intelligence Feed")
                for n in d['news']: st.markdown(f"**[{n.get('publisher')}]** {n.get('title')}"); st.caption(f"🔗 [Link]({n.get('link')})")
                
                with st.expander("📟 Terminal Log", expanded=False):
                    st.markdown(f'<div class="log-terminal"><div class="log-entry">[{datetime.now().strftime("%H:%M:%S")}] SYSTEM: Analytical data for {symbol} processed successfully.</div></div>', unsafe_allow_html=True)

# ==========================================
# MODULE 2: THAI TRADING ANALYSIS (หน้าวิเคราะห์ซื้อ-ขาย)
# ==========================================
elif app_mode == "📈 Thai Trading Analysis":
    with st.sidebar:
        th_ticker = st.text_input("Enter SET Ticker", "CPALL.BK")
        ma_s = st.slider("Fast MA", 5, 50, 20)
        ma_l = st.slider("Slow MA", 50, 200, 50)
    
    st.title("📈 THAI TRADING INTELLIGENCE")
    th_data = fetch_terminal_data([th_ticker.upper()], "TH")
    if th_data:
        d = th_data[th_ticker.upper()]
        df = d['history'].to_frame()
        df['MA_Short'] = df['Close'].rolling(window=ma_s).mean()
        df['MA_Long'] = df['Close'].rolling(window=ma_l).mean()
        
        st.markdown(f"### {th_ticker.upper()} - Market Trend")
        st.line_chart(df[['Close', 'MA_Short', 'MA_Long']])
        
        st.markdown('<div class="academic-box">', unsafe_allow_html=True)
        st.markdown('<p class="academic-label">🔍 Trading Recommendation</p>', unsafe_allow_html=True)
        if df['MA_Short'].iloc[-1] > df['MA_Long'].iloc[-1]:
            st.success("✅ **SIGNAL: BUY** - แนวโน้มเป็นขาขึ้น (Golden Cross Context)")
        else:
            st.error("⚠️ **SIGNAL: SELL/WAIT** - แนวโน้มเป็นขาลง")
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# MODULE 3: GLOBAL MARKET ANALYSIS (ครบถ้วนห้ามลบ)
# ==========================================
elif app_mode == "🌎 Global Market Analysis":
    with st.sidebar:
        g_ticker = st.text_input("Global Ticker", "NVDA")
    
    st.title("🌎 GLOBAL MARKET TERMINAL")
    g_data = fetch_terminal_data([g_ticker.upper()], "Global")
    if g_data:
        d = g_data[g_ticker.upper()]
        st.metric("Price (USD)", f"${d['price']:,.2f}")
        st.line_chart(d['history'].iloc[-252:], color="#00ff88")
        st.subheader("📰 Global News Intelligence")
        for n in d['news']: st.markdown(f"**{n.get('title')}**"); st.caption(f"Source: {n.get('publisher')}")

# --- FOOTER ---
st.markdown(f'<div class="footer">Presented by Run Chantrapipat | © 2026 Climate Finance Hub</div>', unsafe_allow_html=True)
