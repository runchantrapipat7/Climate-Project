import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.graph_objects as go
from datetime import datetime
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="Financial & Climate Intelligence Terminal", layout="wide")

# --- CSS: ULTIMATE DARK TERMINAL UI (รักษาไว้ครบถ้วน 100%) ---
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
    .top-pick-container { border: 1px solid #2ea043; border-radius: 12px; padding: 15px; background: rgba(46,160,67,0.08); box-shadow: 0 0 15px rgba(46,160,67,0.15); margin-bottom: 25px; }
    .top-pick-title { color: #00ff88; font-weight: bold; font-size: 1.05rem; margin: 0; text-align: center; border-bottom: 1px solid rgba(46,160,67,0.3); padding-bottom: 10px; margin-bottom: 15px; }
    .top-pick-item { font-size: 0.88rem; font-weight: bold; margin-bottom: 12px; color: white; display: flex; justify-content: space-between; }
    .log-terminal { background: #000000 !important; border: 1px solid #2ea043 !important; border-radius: 8px; font-family: 'Courier New', Courier, monospace !important; padding: 15px; }
    .log-entry { color: #00ff88; font-size: 0.85rem; margin-bottom: 5px; }
    
    .academic-box { 
        background: rgba(0, 255, 136, 0.03); 
        border: 1px dashed rgba(0, 255, 136, 0.3); 
        border-radius: 10px; 
        padding: 20px; 
        margin-top: 10px; 
    }
    .academic-label { color: #00ff88; font-size: 0.8rem; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
    
    .market-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(0, 255, 136, 0.1);
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 10px;
        transition: all 0.3s ease;
        text-align: center;
    }
    .market-card:hover {
        background: rgba(0, 255, 136, 0.05);
        border-color: rgba(0, 255, 136, 0.4);
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
    }
    .market-label { color: #8b949e; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
    .market-value { color: #ffffff; font-size: 1.15rem; font-weight: 600; font-family: 'Inter', sans-serif; }

    .footer { position: fixed; left: 0; bottom: 0; width: 100%; background-color: rgba(13, 17, 23, 0.95); color: #8b949e; text-align: center; padding: 10px; font-size: 0.8rem; border-top: 1px solid rgba(255, 255, 255, 0.1); z-index: 999; }
    .block-container { padding-bottom: 100px; }
    
    .market-header-sub { color: #8b949e; font-size: 0.9rem; margin-bottom: 20px; font-family: 'Inter', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# --- GLOBAL DATA ENGINE ---
@st.cache_data(ttl=600)
def fetch_pro_data(ticker_list, market_mode="TH"):
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
            
            info = t_obj.info if t_obj.info else {"shortName": symbol}
            news = t_obj.news[:3] if hasattr(t_obj, 'news') else []

            c_beta = 0.0
            if not proxies.empty:
                try:
                    combined = pd.concat([hist.pct_change(), proxies.pct_change()], axis=1).dropna()
                    combined.columns = ['target', 'pttep', 'ea', 'market']
                    bmg = combined['pttep'] - combined['ea']
                    X = sm.add_constant(pd.DataFrame({'Market': combined['market'], 'Carbon': bmg}))
                    c_beta = sm.OLS(combined['target'], X).fit().params.get('Carbon', 0.0)
                except: pass

            full_res[symbol] = {
                "price": float(hist.iloc[-1]),
                "history": hist,
                "c_beta": c_beta,
                "info": info,
                "news": news
            }
        except: continue
    return full_res

# --- SIDEBAR NAVIGATION (3 หน้าหลัก) ---
with st.sidebar:
    st.title("🛡️ Risk Controller")
    terminal_mode = st.radio("Select Module", [
        "🏛️ Thai Climate Risk Project", 
        "📈 Thai Stock Trading Analysis",
        "🌎 Global Market Analysis"
    ])
    st.divider()

# ==========================================
# PAGE 1: Thai Climate Risk Project (โปรเจกต์เดิม 100%)
# ==========================================
if terminal_mode == "🏛️ Thai Climate Risk Project":
    with st.sidebar:
        with st.expander("🔍 Thai Stock Selection", expanded=True):
            t1 = st.text_input("Stock 1", "PTT.BK")
            t2 = st.text_input("Stock 2", "GULF.BK")
            tickers = [t.strip().upper() for t in [t1, t2] if t.strip()]
        
        with st.expander("🌍 Scenario Policy (TCFD)", expanded=True):
            scenario = st.select_slider("Ambition", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
            tax_multiplier = {"Net Zero 2050": 1.5, "Delayed Transition": 1.0, "Current Policy": 0.5}[scenario]
            tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
            flood_risk = st.slider("Flood Exposure (%)", 0, 100, 35)
            wacc = st.slider("WACC (%)", 5.0, 20.0, 12.0) / 100

    st.title("🏛️ CLIMATE RISK AND SUSTAINABLE FINANCE (TCFD)")
    analysis = fetch_pro_data(tickers, market_mode="TH")
    
    if analysis:
        tabs = st.tabs([f"Climate Intel: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                st.markdown(f"### 🇹🇭 {symbol} - Sustainability Report")
                st.markdown(f'<p class="market-header-sub">TCFD Framework • Stock Exchange of Thailand • THB</p>', unsafe_allow_html=True)
                
                # Metrics Row
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Current Price", f"฿{d['price']:,.2f}")
                m2.metric("Climate Beta", f"{d['c_beta']:.4f}")
                m3.metric("Market Cap", f"{d.get('info', {}).get('marketCap', 0)/1e9:.2f}B")
                m4.metric("Risk Status", "Managed" if abs(d['c_beta']) < 0.2 else "High Sensitivity")

                st.line_chart(d['history'].iloc[-252:], color="#00ff88")

                # Academic Box (ห้ามลบ)
                st.markdown('<div class="academic-box">', unsafe_allow_html=True)
                st.markdown('<p class="academic-label">🔬 Quantitative Climate Risk Analytics (TCFD Framework)</p>', unsafe_allow_html=True)
                q1, q2, q3 = st.columns(3); dynamic_trans = d['c_beta'] * 100 * tax_multiplier
                climate_var = abs(dynamic_trans) * 0.1
                with q1: st.write(f"📊 **Sensitivity:** **{d['c_beta']:.4f}**")
                with q2: st.write(f"📉 **Climate VaR:** <span style='color:#ff4b4b;'>**{climate_var:,.2f}%**</span>", unsafe_allow_html=True)
                with q3: st.write(f"🏢 **Sector Vulnerability:** {'High' if abs(d['c_beta']) > 0.3 else 'Standard'}")
                st.markdown('</div>', unsafe_allow_html=True)

                # Gauge & Waterfall (ห้ามลบ)
                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    fig_g = go.Figure(go.Indicator(mode="gauge+number", value=dynamic_trans, title={'text': "Transition Sensitivity"}, gauge={'axis': {'range': [-50, 50]}, 'bar': {'color': "white"}, 'steps': [{'range': [-50, 0], 'color': '#238636'}, {'range': [0, 20], 'color': '#f1e05a'}, {'range': [20, 50], 'color': '#da3633'}]}))
                    fig_g.update_layout(height=280, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=50, b=0))
                    st.plotly_chart(fig_g, use_container_width=True, key=f"th_cli_gauge_{symbol}")
                with c2:
                    raw_cap = d.get('info', {}).get('marketCap', 1e9); mkt_cap_mb = float(raw_cap)/1e6
                    val_impact = (tax_price * 1000) / wacc / 1e6; adj_val = mkt_cap_mb - val_impact
                    fig_w = go.Figure(go.Waterfall(orientation="v", x=["Initial", "Climate Loss", "Adjusted"], y=[mkt_cap_mb, -val_impact, adj_val], textposition="outside", increasing={"marker":{"color":"#2ea043"}}, decreasing={"marker":{"color":"#da3633"}}, totals={"marker":{"color":"#1f6feb"}}))
                    fig_w.update_layout(height=280, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, margin=dict(t=20, b=0))
                    st.plotly_chart(fig_w, use_container_width=True, key=f"th_cli_water_{symbol}")

# ==========================================
# PAGE 2: Thai Stock Trading Analysis (วิเคราะห์ซื้อ-ขายหุ้นไทย)
# ==========================================
elif terminal_mode == "📈 Thai Stock Trading Analysis":
    with st.sidebar:
        with st.expander("📈 Trading Parameters", expanded=True):
            th_ticker = st.text_input("Enter SET Ticker (e.g., CPALL.BK)", "CPALL.BK")
            ma_s = st.slider("Short MA", 5, 50, 20)
            ma_l = st.slider("Long MA", 50, 200, 50)
            rsi_p = st.slider("RSI Window", 7, 30, 14)
    
    st.title("📈 THAI STOCK TECHNICAL TRADING TERMINAL")
    th_analysis = fetch_pro_data([th_ticker.upper()], market_mode="TH")
    
    if th_analysis:
        d = th_analysis[th_ticker.upper()]
        df = d['history'].to_frame()
        # Technicals
        df['MA_Short'] = df['Close'].rolling(window=ma_s).mean()
        df['MA_Long'] = df['Close'].rolling(window=ma_l).mean()
        delta = df['Close'].diff(); gain = (delta.where(delta > 0, 0)).rolling(window=rsi_p).mean(); loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_p).mean()
        df['RSI'] = 100 - (100 / (1 + (gain/loss)))
        
        st.markdown(f"### 🇹🇭 {th_ticker.upper()} - Trading Analytics")
        st.markdown(f'<p class="market-header-sub">Stock Exchange of Thailand • Real Time Technical Signal • THB</p>', unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Price", f"฿{d['price']:,.2f}", f"{((d['price']/df['Close'].iloc[-2])-1)*100:+.2f}%")
        c2.metric("Trend", "📈 BULLISH" if df['MA_Short'].iloc[-1] > df['MA_Long'].iloc[-1] else "📉 BEARISH")
        c3.metric("RSI", f"{df['RSI'].iloc[-1]:.2f}")
        c4.metric("52W High", f"฿{d.get('info', {}).get('fiftyTwoWeekHigh', 0):,.2f}")

        # Chart
        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(x=df.index, y=df['Close'], name="Price", line=dict(color='#00ff88')))
        fig_t.add_trace(go.Scatter(x=df.index, y=df['MA_Short'], name=f"MA{ma_s}", line=dict(color='#f1e05a', dash='dash')))
        fig_t.add_trace(go.Scatter(x=df.index, y=df['MA_Long'], name=f"MA{ma_l}", line=dict(color='#da3633', dash='dot')))
        fig_t.update_layout(height=450, template="plotly_dark", margin=dict(l=0,r=0,t=20,b=0))
        st.plotly_chart(fig_t, use_container_width=True)

        st.markdown('<div class="academic-box">', unsafe_allow_html=True)
        st.markdown('<p class="academic-label">🔍 Terminal Trade Recommendation</p>', unsafe_allow_html=True)
        if df['MA_Short'].iloc[-1] > df['MA_Long'].iloc[-1] and df['RSI'].iloc[-1] < 70:
            st.success("🌟 **Signal: BUY / ACCUMULATE** - แนวโน้มเป็นขาขึ้นและราคายังไม่เข้าเขตซื้อมากเกินไป")
        elif df['MA_Short'].iloc[-1] < df['MA_Long'].iloc[-1] and df['RSI'].iloc[-1] > 30:
            st.error("⚠️ **Signal: SELL / REDUCE** - แนวโน้มหลักเป็นขาลง แนะนำให้ระมัดระวัง")
        else:
            st.warning("🔄 **Signal: NEUTRAL** - ราคากำลังสร้างฐาน หรือสัญญาณยังไม่ชัดเจน")
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# PAGE 3: Global Market Analysis (ห้ามย่อ ห้ามลบจากเดิม)
# ==========================================
elif terminal_mode == "🌎 Global Market Analysis":
    with st.sidebar:
        with st.expander("🔍 Global Stock Entry", expanded=True):
            g1 = st.text_input("Global Stock 1", "AAPL")
            g2 = st.text_input("Global Stock 2", "NVDA")
            global_tickers = [t.strip().upper() for t in [g1, g2] if t.strip()]
        
        with st.expander("📈 Strategy Settings", expanded=True):
            g_ma_s = st.slider("Fast MA", 5, 50, 20)
            g_ma_l = st.slider("Slow MA", 50, 200, 50)
            g_rsi = st.slider("RSI Window", 7, 30, 14)

    st.title("🌎 GLOBAL MARKET TECHNICAL INTELLIGENCE")
    g_data = fetch_pro_data(global_tickers, market_mode="Global")
    if g_data:
        g_tabs = st.tabs([f"Analysis: {s}" for s in g_data.keys()])
        for i, (symbol, d) in enumerate(g_data.keys()):
            with g_tabs[i]:
                # ข้อมูลเดิมทั้งหมด (Technical, Deep Dive, News)
                dat = g_data[symbol]
                df = dat['history'].to_frame()
                df['MA_S'] = df['Close'].rolling(window=g_ma_s).mean(); df['MA_L'] = df['Close'].rolling(window=g_ma_l).mean()
                delta = df['Close'].diff(); gain = (delta.where(delta > 0, 0)).rolling(window=g_rsi).mean(); loss = (-delta.where(delta < 0, 0)).rolling(window=g_rsi).mean()
                df['RSI'] = 100 - (100 / (1 + (gain/loss)))
                
                st.markdown(f"### 🌎 {symbol} - {dat.get('info', {}).get('exchange', 'NASDAQ')}")
                st.markdown(f'<p class="market-header-sub">Global Real Time Price • USD</p>', unsafe_allow_html=True)
                
                st.line_chart(df[['Close', 'MA_S', 'MA_L']], color=["#00ff88", "#f1e05a", "#da3633"])
                
                st.divider()
                st.subheader("📊 Fundamental Deep Dive")
                p1, p2 = st.columns([1, 2])
                with p1:
                    ret_1y = ((dat['price']/df['Close'].iloc[-252])-1)*100
                    st.table(pd.DataFrame({"Period": ["1 Year Return"], "Return": [f"{ret_1y:+.2f}%"]}))
                with p2:
                    inf = dat.get('info', {})
                    st.write(f"🏢 **Name:** {inf.get('longName')}")
                    st.write(f"💰 **Div Yield:** {inf.get('dividendYield', 0)*100:.2f}%")
                    st.write(f"📈 **52W High:** ${inf.get('fiftyTwoWeekHigh', 0):,.2f}")

# --- FOOTER ---
st.markdown(f'<div class="footer">🏛️ Climate & Financial Terminal | <b>Presented by Run Chantrapipat</b> | © 2026</div>', unsafe_allow_html=True)
