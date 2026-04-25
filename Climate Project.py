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

# --- CSS: ULTIMATE DARK TERMINAL UI (คงเดิม + อัปเกรด Market Cards) ---
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
    
    /* Academic Section Style */
    .academic-box { 
        background: rgba(0, 255, 136, 0.03); 
        border: 1px dashed rgba(0, 255, 136, 0.3); 
        border-radius: 10px; 
        padding: 20px; 
        margin-top: 10px; 
    }
    .academic-label { color: #00ff88; font-size: 0.8rem; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
    
    /* --- NEW: Market Summary Modern Card Style --- */
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
    .market-label {
        color: #8b949e;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .market-value {
        color: #ffffff;
        font-size: 1.15rem;
        font-weight: 600;
        font-family: 'Inter', sans-serif;
    }

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
        t2 = st.text_input("Stock 2", "GULF.BK")
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
            
            info = {}
            try:
                info = t_obj.info if t_obj.info else {}
                fast = t_obj.fast_info
                if fast:
                    info['marketCap'] = info.get('marketCap') or fast.get('market_cap')
            except: info = {"shortName": symbol}

            news = []
            try: news = t_obj.news[:3]
            except: pass

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
        except: continue
    return full_res

# --- MAIN DISPLAY ---
st.title("🏛️ CLIMATE RISK AND SUSTAINABLE FINANCE 🏛️")

if not tickers:
    st.info("💡 กรุณาระบุชื่อหุ้นใน Sidebar (เช่น PTT.BK) เพื่อเริ่มต้น")
else:
    analysis = fetch_pro_data(tickers)
    if analysis:
        # Overview Cards
        cols = st.columns(len(analysis))
        for i, (symbol, d) in enumerate(analysis.items()):
            cols[i].metric(f"💎 {symbol}", f"{d['price']:,.2f}", delta=f"C-Beta: {d['c_beta']:.3f}")

        # Intelligence Box Tabs
        tabs = st.tabs([f"Intelligence Center: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                # 1. กราฟราคา
                st.subheader(f"📈 Price Performance: {symbol}")
                st.line_chart(d['history'], color="#00ff88")

                # 2. Market Intelligence (Modern UI Updated)
                st.subheader(f"📊 Market Intelligence: {symbol}")
                inf = d.get('info', {})
                
                def get_val(key, style="{:,.2f}", mult=1):
                    v = inf.get(key)
                    if v is None or v == 0: return "N/A"
                    try: return style.format(float(v) * mult)
                    except: return str(v)

                # แสดงผลแบบ Grid 3 คอลัมน์
                m_c1, m_c2, m_c3 = st.columns(3)
                m_c4, m_c5, m_c6 = st.columns(3)

                with m_c1:
                    st.markdown(f'<div class="market-card"><div class="market-label">Market Cap</div><div class="market-value">{get_val("marketCap", "{:,.0f}")}</div></div>', unsafe_allow_html=True)
                with m_c2:
                    st.markdown(f'<div class="market-card"><div class="market-label">Trailing P/E</div><div class="market-value">{get_val("trailingPE")}</div></div>', unsafe_allow_html=True)
                with m_c3:
                    st.markdown(f'<div class="market-card"><div class="market-label">Beta (5Y)</div><div class="market-value">{get_val("beta")}</div></div>', unsafe_allow_html=True)
                with m_c4:
                    st.markdown(f'<div class="market-card"><div class="market-label">Profit Margin</div><div class="market-value">{get_val("profitMargins", "{:.2%}")}</div></div>', unsafe_allow_html=True)
                with m_c5:
                    st.markdown(f'<div class="market-card"><div class="market-label">Div. Yield</div><div class="market-value">{get_val("dividendYield", "{:.2%}")}</div></div>', unsafe_allow_html=True)
                with m_c6:
                    st.markdown(f'<div class="market-card"><div class="market-label">Debt/Equity</div><div class="market-value">{get_val("debtToEquity")}</div></div>', unsafe_allow_html=True)

                st.divider()
                # 3. Risk Matrix (ส่วนเดิมของคุณ 100%)
                st.subheader("🛡️ Comprehensive Climate Risk Matrix")
                de_raw = inf.get('debtToEquity')
                de_ratio = float(de_raw) if de_raw and de_raw != 'N/A' else 100.0
                dynamic_trans = d['c_beta'] * 100 * tax_multiplier
                credit_risk = "High" if (de_ratio > 150 or abs(dynamic_trans) > 25) else "Low"
                op_risk = "High" if flood_risk > 60 else "Low"
                
                r1, r2, r3, r4 = st.columns(4)
                r1.warning(f"💳 Credit: {credit_risk}")
                r2.error(f"🏗️ Operational: {op_risk}")
                r3.info(f"💧 Liquidity: Low")
                r4.success(f"⚖️ Liability: Low")

                # --- [ส่วนที่เพิ่ม: ปรับแต่งค่า Indicator] ---
                with st.expander("🔬 Adjust Quantitative Indicators (Real-time Tuning)", expanded=True):
                    st.markdown("*หากค่าเริ่มต้นเป็น 0.0000 ให้ปรับ Beta Offset เพื่อทดสอบ Scenario*")
                    p_col1, p_col2, p_col3 = st.columns(3)
                    with p_col1:
                        # ตัวบวกค่าพื้นฐาน (Offset) เพื่อแก้ปัญหา 0.0000
                        beta_offset = st.slider(f"Manual Beta Offset ({symbol})", -1.0, 1.0, 0.0, 0.01, key=f"off_{symbol}")
                    with p_col2:
                        # ตัวคูณแรงกระแทก
                        stress_factor = st.slider(f"Stress Multiplier ({symbol})", 0.5, 5.0, 1.0, 0.1, key=f"stress_{symbol}")
                    with p_col3:
                        # ปรับระดับความรุนแรงของ Shock
                        shock_val = st.slider(f"Policy Shock % ({symbol})", 1, 100, 10, key=f"shock_{symbol}") / 100
                
                # คำนวณค่าใหม่ที่ตอบสนองต่อการปรับจูน
                adjusted_c_beta = (d['c_beta'] + beta_offset) * stress_factor
                climate_var = abs(adjusted_c_beta) * shock_val * 100
                # ------------------------------------------

                # --- 🟢 ส่วน Quantitative Academic Analysis (คงเดิม แต่เปลี่ยนตัวแปรให้ Dynamic) ---
                st.markdown('<div class="academic-box">', unsafe_allow_html=True)
                st.markdown('<p class="academic-label">🔬 Quantitative Climate Risk Analytics (TCFD Framework)</p>', unsafe_allow_html=True)
                
                q1, q2, q3 = st.columns(3)
                
                with q1:
                    st.write("📊 **Climate Sensitivity Index**")
                    # แสดงผลตัวแปรใหม่ที่ปรับได้
                    st.write(f"ค่าการตอบสนองต่อราคาคาร์บอน: **{adjusted_c_beta:.4f}**")
                    st.caption(f"อ้างอิงจากความสัมพันธ์ (Original: {d['c_beta']:.4f} + Offset: {beta_offset:.2f})")
                
                with q2:
                    st.write("📉 **Climate Value-at-Risk (CVaR)**")
                    # แสดงผลตัวแปรใหม่ที่ปรับได้
                    st.write(f"ความเสี่ยงมูลค่าที่อาจสูญเสีย: <span style='color:#ff4b4b;'>**{climate_var:,.2f}%**</span>", unsafe_allow_html=True)
                    st.caption(f"ประมาณการความเสียหายกรณี Shock {shock_val*100:.0f}%")

                with q3:
                    st.write("🏢 **Sector Vulnerability**")
                    risk_level = "High Exposure" if abs(adjusted_c_beta) > 0.3 else "Standard Exposure"
                    st.write(f"ระดับการปะทะ: **{risk_level}**")
                    st.caption("การประเมินความเปราะบางรายตัวเทียบกับค่าเฉลี่ยอุตสาหกรรมในบริบทของ Transition Risk")
                st.markdown('</div>', unsafe_allow_html=True)

                st.divider()
                # 4. Gauge & Waterfall (คงเดิม 100%)
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
                    raw_cap = inf.get('marketCap')
                    mkt_cap_mb = float(raw_cap)/1e6 if raw_cap and raw_cap != 0 else 1e5
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
st.markdown(f'<div class="footer">🏛️ Climate Risk And Sustainable Finance | <b>Presented by Run Chantrapipat</b> | © 2026</div>', unsafe_allow_html=True)
