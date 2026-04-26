import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.graph_objects as go
from datetime import datetime
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="Climate & Global Finance Pro Terminal", layout="wide")

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
    .top-pick-container { border: 1px solid #2ea043; border-radius: 12px; padding: 15px; background: rgba(46,160,67,0.08); margin-bottom: 25px; }
    .top-pick-title { color: #00ff88; font-weight: bold; font-size: 1.05rem; margin: 0; text-align: center; border-bottom: 1px solid rgba(46,160,67,0.3); padding-bottom: 10px; margin-bottom: 15px; }
    .top-pick-item { font-size: 0.88rem; font-weight: bold; margin-bottom: 12px; color: white; display: flex; justify-content: space-between; }
    .log-terminal { background: #000000 !important; border: 1px solid #2ea043 !important; border-radius: 8px; font-family: 'Courier New', Courier, monospace !important; padding: 15px; }
    .log-entry { color: #00ff88; font-size: 0.85rem; margin-bottom: 5px; }
    .academic-box { background: rgba(0, 255, 136, 0.03); border: 1px dashed rgba(0, 255, 136, 0.3); border-radius: 10px; padding: 20px; margin-top: 10px; }
    .academic-label { color: #00ff88; font-size: 0.8rem; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
    .market-card { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(0, 255, 136, 0.1); border-radius: 12px; padding: 18px; margin-bottom: 10px; transition: all 0.3s ease; text-align: center; }
    .market-card:hover { background: rgba(0, 255, 136, 0.05); border-color: rgba(0, 255, 136, 0.4); transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4); }
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
            
            info = {}
            try: info = t_obj.info if t_obj.info else {}
            except: info = {"shortName": symbol}

            news = []
            try: news = t_obj.news[:3]
            except: pass

            c_beta = 0.0
            if not proxies.empty:
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
    terminal_mode = st.radio("Select Module", ["🏛️ Thai Climate Risk", "🌎 Global Technical Analysis", "📈 Thai Technical Analysis"])
    st.divider()

# ==========================================
# MODULE 1: THAI CLIMATE RISK (ฟีเจอร์เดิมครบ 100%)
# ==========================================
if terminal_mode == "🏛️ Thai Climate Risk":
    @st.cache_data(ttl=3600)
    def get_real_top_picks_5():
        candidate_tickers = ["PTT.BK", "CPALL.BK", "AOT.BK", "KBANK.BK", "EA.BK", "GULF.BK"]
        picks = []
        try:
            data = yf.download(candidate_tickers, period="5d", progress=False)['Volume']
            for t in candidate_tickers:
                if t in data.columns:
                    v = data[t].dropna()
                    if not v.empty: picks.append({"symbol": t, "volume": v.iloc[-1]})
        except: pass
        return sorted(picks, key=lambda x: x['volume'], reverse=True)[:5]

    with st.sidebar:
        top_stocks = get_real_top_picks_5()
        stocks_html = "".join([f'<div class="top-pick-item"><span>{s["symbol"]}</span><span style="color:#8b949e; font-size:0.7rem;">Active Vol.</span></div>' for s in top_stocks])
        st.markdown(f'<div class="top-pick-container"><p class="top-pick-title">🌟 หุ้นเด่นวันนี้ (Real-time)</p>{stocks_html}</div>', unsafe_allow_html=True)
        with st.expander("🔍 Stock Selection", expanded=True):
            t1 = st.text_input("Stock 1", "PTT.BK"); t2 = st.text_input("Stock 2", "GULF.BK"); t3 = st.text_input("Stock 3", "")
        with st.expander("🌍 Scenario Policy (TCFD)", expanded=True):
            scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
            tax_multiplier = {"Net Zero 2050": 1.5, "Delayed Transition": 1.0, "Current Policy": 0.5}[scenario]
            tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
            flood_risk = st.slider("Flood Exposure (%)", 0, 100, 35)
            wacc = st.slider("WACC (%)", 5.0, 20.0, 12.0) / 100
        tickers = [t.strip().upper() for t in [t1, t2, t3] if t.strip()]

    st.title("🏛️ THAI CLIMATE RISK AND FINANCIAL DEEP DIVE")
    if tickers:
        analysis = fetch_pro_data(tickers, market_mode="TH")
        if analysis:
            tabs = st.tabs([f"Intelligence: {s}" for s in analysis.keys()])
            for i, (symbol, d) in enumerate(analysis.items()):
                with tabs[i]:
                    st.markdown(f"### 🇹🇭 {symbol} - Sustainability Report")
                    st.markdown(f'<p class="market-header-sub">SET - Thailand Real Time Price • THB</p>', unsafe_allow_html=True)
                    m1, m2, m3, m4 = st.columns(4); curr_p = d['price']; prev_p = d['history'].iloc[-2]; p_change = ((curr_p - prev_p) / prev_p) * 100
                    m1.metric("Current Price", f"฿{curr_p:,.2f}", f"{p_change:+.2f}%"); m2.metric("Climate Beta", f"{d['c_beta']:.4f}"); m3.metric("Market Cap", f"{d.get('info', {}).get('marketCap', 0)/1e9:.2f}B"); m4.metric("Status", "STABLE" if abs(p_change) < 2 else "VOLATILE")
                    st.line_chart(d['history'].iloc[-252:], color="#00ff88")
                    st.divider(); st.subheader("🛡️ Climate Risk Matrix & Analytics")
                    q1, q2, q3 = st.columns(3); trans_impact = d['c_beta'] * 100 * tax_multiplier
                    with q1: st.write(f"📊 **Sensitivity:** {d['c_beta']:.4f}"); with q2: st.write(f"📉 **Climate VaR:** {abs(trans_impact)*0.1:.2f}%"); with q3: st.write(f"🏢 **Sector:** {d['info'].get('sector','N/A')}")
                    c1, c2 = st.columns(2)
                    with c1:
                        fig_g = go.Figure(go.Indicator(mode="gauge+number", value=trans_impact, title={'text': "Transition Sensitivity"}, gauge={'axis':{'range':[-50,50]}, 'bar':{'color':"white"}, 'steps':[{'range':[-50,0],'color':'#238636'},{'range':[0,20],'color':'#f1e05a'},{'range':[20,50],'color':'#da3633'}]}))
                        st.plotly_chart(fig_g, use_container_width=True, key=f"cli_g_{symbol}")
                    with c2:
                        raw_cap = d['info'].get('marketCap', 1e9)/1e6; val_loss = (tax_price*1000)/wacc/1e6
                        fig_w = go.Figure(go.Waterfall(orientation="v", x=["Initial", "Climate Loss", "Adjusted"], y=[raw_cap, -val_loss, raw_cap-val_loss], increasing={"marker":{"color":"#2ea043"}}, decreasing={"marker":{"color":"#da3633"}}, totals={"marker":{"color":"#1f6feb"}}))
                        st.plotly_chart(fig_w, use_container_width=True, key=f"cli_w_{symbol}")

# ==========================================
# MODULE 2: GLOBAL TECHNICAL ANALYSIS (ฟีเจอร์เดิมครบ 100%)
# ==========================================
elif terminal_mode == "🌎 Global Technical Analysis":
    with st.sidebar:
        with st.expander("🔍 Global Stock Selection", expanded=True):
            g1 = st.text_input("Global Stock 1", "AAPL"); g2 = st.text_input("Global Stock 2", "NVDA"); g3 = st.text_input("Global Stock 3", "TSLA")
            g_tickers = [t.strip().upper() for t in [g1, g2, g3] if t.strip()]
        with st.expander("📈 Strategy Settings", expanded=True):
            ma_s = st.slider("Short MA", 5, 50, 20); ma_l = st.slider("Long MA", 50, 200, 50); rsi_w = st.slider("RSI Period", 7, 30, 14)

    st.title("🌎 GLOBAL MARKET TECHNICAL INTELLIGENCE")
    if g_tickers:
        g_data = fetch_pro_data(g_tickers, market_mode="Global")
        if g_data:
            g_tabs = st.tabs([f"Analysis: {s}" for s in g_data.keys()])
            for i, (symbol, d) in enumerate(g_data.items()):
                with g_tabs[i]:
                    st.markdown(f"### 🌎 {symbol} - Global Market Report")
                    df = d['history'].to_frame(); df['MA_S'] = df['Close'].rolling(window=ma_s).mean(); df['MA_L'] = df['Close'].rolling(window=ma_l).mean()
                    delta = df['Close'].diff(); gain = (delta.where(delta > 0, 0)).rolling(window=rsi_w).mean(); loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_w).mean(); df['RSI'] = 100 - (100 / (1 + (gain/loss)))
                    c1, c2, c3, c4 = st.columns(4); rsi_val = df['RSI'].iloc[-1]; trend = "📈 BULLISH" if df['MA_S'].iloc[-1] > df['MA_L'].iloc[-1] else "📉 BEARISH"
                    c1.metric("Price", f"${d['price']:,.2f}"); c2.metric("Trend", trend); c3.metric("RSI", f"{rsi_val:.2f}"); c4.metric("Status", "Neutral")
                    st.line_chart(df[['Close', 'MA_S', 'MA_L']], color=["#00ff88", "#f1e05a", "#da3633"])
                    st.divider(); st.subheader(f"📊 Performance & Fundamentals: {symbol}")
                    p1, p2 = st.columns([1, 2]); inf = d.get('info', {})
                    with p1: st.table(pd.DataFrame({"Period": ["1Y Return"], "Return": [f"{((d['price']/df['Close'].iloc[-252])-1)*100:+.2f}%"]}))
                    with p2:
                        st.write(f"🏢 **Name:** {inf.get('longName', symbol)}"); st.write(f"💰 **Yield:** {inf.get('dividendYield',0)*100:.2f}%"); st.write(f"📈 **52W High:** ${inf.get('fiftyTwoWeekHigh',0):,.2f}")

# ==========================================
# MODULE 3: THAI TECHNICAL ANALYSIS (อัปเกรดให้เหมือน Global ตามภาพ 100%)
# ==========================================
elif terminal_mode == "📈 Thai Technical Analysis":
    with st.sidebar:
        with st.expander("🔍 Thai Stock Selection", expanded=True):
            t1_th = st.text_input("Thai Stock 1", "CPALL.BK"); t2_th = st.text_input("Thai Stock 2", "AOT.BK"); t3_th = st.text_input("Thai Stock 3", "")
            th_tr_tickers = [t.strip().upper() for t in [t1_th, t2_th, t3_th] if t.strip()]
        with st.expander("📈 Strategy Settings", expanded=True):
            ma_s_th = st.slider("Short MA", 5, 50, 20); ma_l_th = st.slider("Long MA", 50, 200, 50); rsi_w_th = st.slider("RSI Period", 7, 30, 14)

    st.title("📈 THAI STOCK TECHNICAL TRADING TERMINAL")
    if th_tr_tickers:
        th_data = fetch_pro_data(th_tr_tickers, market_mode="TH")
        if th_data:
            th_tabs = st.tabs([f"Trading: {s}" for s in th_data.keys()])
            for i, (symbol, d) in enumerate(th_data.items()):
                with th_tabs[i]:
                    st.markdown(f"### 🇹🇭 {symbol} - Stock Exchange of Thailand")
                    st.markdown(f'<p class="market-header-sub">SET Real Time Price • Technical Signal • THB</p>', unsafe_allow_html=True)
                    
                    df = d['history'].to_frame()
                    df['MA_S'] = df['Close'].rolling(window=ma_s_th).mean()
                    df['MA_L'] = df['Close'].rolling(window=ma_l_th).mean()
                    # RSI Calculation
                    delta = df['Close'].diff(); gain = (delta.where(delta > 0, 0)).rolling(window=rsi_w_th).mean(); loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_w_th).mean()
                    df['RSI'] = 100 - (100 / (1 + (gain/loss)))
                    # MACD Calculation
                    exp1 = df['Close'].ewm(span=12, adjust=False).mean(); exp2 = df['Close'].ewm(span=26, adjust=False).mean()
                    df['MACD'] = exp1 - exp2; df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

                    # 1. METRICS BOX (4 ช่องเหมือนภาพ)
                    c1, c2, c3, c4 = st.columns(4)
                    rsi_v = df['RSI'].iloc[-1]; trend_v = "📈 BULLISH" if df['MA_S'].iloc[-1] > df['MA_L'].iloc[-1] else "📉 BEARISH"
                    c1.metric("Current Price", f"฿{d['price']:,.2f}", f"{((d['price']/df['Close'].iloc[-2])-1)*100:+.2f}%")
                    c2.metric("Trend Status", trend_v, delta_color="normal" if "BULL" in trend_v else "inverse")
                    c3.metric("RSI Momentum", f"{rsi_v:.2f}", "Extreme" if (rsi_v > 70 or rsi_v < 30) else "Normal")
                    macd_v = "BUY" if df['MACD'].iloc[-1] > df['Signal'].iloc[-1] else "SELL"
                    c4.metric("MACD Signal", macd_v)

                    # 2. CHART (เหมือนภาพ)
                    fig_th = go.Figure()
                    fig_th.add_trace(go.Scatter(x=df.index, y=df['Close'], name="Price", line=dict(color='#00ff88')))
                    fig_th.add_trace(go.Scatter(x=df.index, y=df['MA_S'], name=f"MA {ma_s_th}", line=dict(color='#f1e05a', dash='dash')))
                    fig_th.add_trace(go.Scatter(x=df.index, y=df['MA_L'], name=f"MA {ma_l_th}", line=dict(color='#da3633', dash='dot')))
                    fig_th.update_layout(height=450, template="plotly_dark", margin=dict(l=0,r=0,t=20,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_th, use_container_width=True, key=f"th_tr_chart_{symbol}")

                    # 3. MARKET INTELLIGENCE GRID (เหมือนภาพ)
                    st.divider(); st.subheader("📊 Market Intelligence Grid")
                    inf = d.get('info', {})
                    def get_f(key, style="{:,.2f}"):
                        v = inf.get(key); return style.format(float(v)) if (v and v != 'N/A') else "N/A"
                    mc1, mc2, mc3 = st.columns(3); mc4, mc5, mc6 = st.columns(3)
                    with mc1: st.markdown(f'<div class="market-card"><div class="market-label">P/E Ratio</div><div class="market-value">{get_f("trailingPE")}</div></div>', unsafe_allow_html=True)
                    with mc2: st.markdown(f'<div class="market-card"><div class="market-label">P/B Ratio</div><div class="market-value">{get_f("priceToBook")}</div></div>', unsafe_allow_html=True)
                    with mc3: st.markdown(f'<div class="market-card"><div class="market-label">Div. Yield</div><div class="market-value">{get_f("dividendYield", "{:.2%}")}</div></div>', unsafe_allow_html=True)
                    with mc4: st.markdown(f'<div class="market-card"><div class="market-label">Beta (5Y)</div><div class="market-value">{get_f("beta")}</div></div>', unsafe_allow_html=True)
                    with mc5: st.markdown(f'<div class="market-card"><div class="market-label">Profit Margin</div><div class="market-value">{get_f("profitMargins", "{:.2%}")}</div></div>', unsafe_allow_html=True)
                    with mc6: st.markdown(f'<div class="market-card"><div class="market-label">Debt/Equity</div><div class="market-value">{get_f("debtToEquity")}</div></div>', unsafe_allow_html=True)

                    # 4. DEEP DIVE (เหมือนภาพ)
                    st.divider(); st.subheader(f"📊 Deep Dive: {symbol} Financials & Performance")
                    curr_p = d['price']; ret_1m = ((curr_p / df['Close'].iloc[-21]) - 1) * 100; ret_1y = ((curr_p / df['Close'].iloc[-252]) - 1) * 100
                    p1, p2 = st.columns([1, 2])
                    with p1:
                        st.markdown("**Performance Tracker**")
                        st.table(pd.DataFrame({"Period": ["1 Month", "1 Year"], "Return": [f"{ret_1m:+.2f}%", f"{ret_1y:+.2f}%"]}))
                    with p2:
                        st.markdown("**Fundamental Highlights**")
                        f1, f2 = st.columns(2)
                        with f1:
                            st.write(f"🏢 **Full Name:** {inf.get('longName', symbol)}"); st.write(f"📈 **52W High:** ฿{inf.get('fiftyTwoWeekHigh', 0):,.2f}")
                        with f2:
                            st.write(f"🌎 **Sector:** {inf.get('sector', 'N/A')}"); st.write(f"📉 **52W Low:** ฿{inf.get('fiftyTwoWeekLow', 0):,.2f}")

                    # 5. RECOMMENDATION BOX (เหมือนภาพ)
                    st.markdown('<div class="academic-box"><p class="academic-label">🔍 Terminal Trade Recommendation</p>', unsafe_allow_html=True)
                    if "BULL" in trend_v and rsi_v < 65: st.success(f"🌟 **Strong Buy Signal:** {symbol} มีแนวโน้มขาขึ้นและราคายังมี Upside")
                    elif "BEAR" in trend_v and rsi_v > 35: st.error(f"⚠️ **Bearish Alert:** {symbol} อยู่ในแนวโน้มขาลง แนะนำให้ระวังแรงขาย")
                    else: st.warning("🔄 **Neutral:** สัญญาณยังไม่ชัดเจน แนะนำให้รอดูการยืนเหนือเส้นค่าเฉลี่ย"); st.markdown('</div>', unsafe_allow_html=True)

# --- FOOTER ---
st.markdown(f'<div class="footer">🏛️ Climate & Global Finance Terminal | <b>Presented by Run Chantrapipat</b> | © 2026</div>', unsafe_allow_html=True)
