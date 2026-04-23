import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.graph_objects as go
from datetime import datetime
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="Sustainable Finance Intelligence Pro", layout="wide")

# --- CSS: ULTIMATE DARK MODE & GLASSMORPHISM ---
st.markdown("""
    <style>
    .main { background: radial-gradient(circle at top right, #1a1f2e, #0d1117); color: white; }
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px; padding: 15px;
    }
    .insight-card {
        background: rgba(0, 210, 106, 0.08);
        border-left: 5px solid #00d26a;
        padding: 20px; border-radius: 10px; margin-top: 15px;
    }
    .risk-card {
        background: rgba(255, 75, 75, 0.08);
        border-left: 5px solid #ff4b4b;
        padding: 20px; border-radius: 10px; margin-top: 15px;
    }
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: rgba(13, 17, 23, 0.95);
        color: #8b949e; text-align: center; padding: 12px;
        font-size: 0.85rem; border-top: 1px solid rgba(255, 255, 255, 0.1); z-index: 999;
    }
    .block-container { padding-bottom: 80px; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: ALL FEATURES PRESERVED ---
with st.sidebar:
    st.title("🛡️ Risk Controller")
    st.header("🔍 ระบุชื่อหุ้นหรือกองทุน (Stock or Bond)")
    t1 = st.text_input("Asset 1", "PTT.BK")
    t2 = st.text_input("Asset 2", "EA.BK")
    t3 = st.text_input("Asset 3", "TPIPP.BK")
    tickers = [t.strip().upper() for t in [t1, t2, t3] if t.strip()]

    st.divider()
    st.header("🌍 Scenario & Policy (TCFD)")
    scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
    tax_mult = {"Net Zero 2050": 1.6, "Delayed Transition": 1.0, "Current Policy": 0.4}[scenario]
    tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    flood_exp = st.slider("Flood Exposure (%)", 0, 100, 78)
    wacc_val = st.slider("WACC (%)", 5.0, 15.0, 7.9) / 100

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
            
            # Transition Risk Modeling
            c_beta = 0.0
            if not proxies.empty:
                try:
                    temp_df = pd.concat([hist, proxies], axis=1).pct_change().dropna()
                    bmg = temp_df["PTTEP.BK"] - temp_df["EA.BK"]
                    X = sm.add_constant(pd.DataFrame({'Market': temp_df["^SET.BK"], 'Carbon': bmg}))
                    model = sm.OLS(temp_df[symbol], X).fit()
                    c_beta = model.params.get('Carbon', 0.0)
                except: pass

            full_res[symbol] = {
                "price": float(hist.iloc[-1]),
                "history": hist,
                "c_beta": c_beta,
                "info": t_obj.info if t_obj.info else {},
                "news": t_obj.news[:3] if t_obj.news else []
            }
        except: continue
    return full_res

# --- MAIN DISPLAY ---
st.title("🏛️ SUSTAINABLE FINANCE ASSET TERMINAL")

if tickers:
    with st.spinner('กำลังดึงข้อมูลและประมวลผลความเสี่ยง...'):
        analysis = fetch_pro_data(tickers)
    
    if analysis:
        # Overview Comparative Metrics
        cols = st.columns(len(analysis))
        for i, (symbol, d) in enumerate(analysis.items()):
            cols[i].metric(f"💎 {symbol}", f"{d['price']:,.2f}", delta=f"C-Beta: {d['c_beta']:.3f}")

        # Analysis Tabs
        tabs = st.tabs([f"Intelligence Center: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                c1, c2 = st.columns(2)
                
                with c1:
                    st.subheader("🔥 Transition Risk Sensitivity")
                    # DYNAMIC GAUGE
                    risk_val = d['c_beta'] * 100 * tax_mult
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number", value = risk_val,
                        gauge = {
                            'axis': {'range': [-50, 50], 'tickcolor': "white"},
                            'bar': {'color': "white"},
                            'steps': [
                                {'range': [-50, 0], 'color': '#238636'},
                                {'range': [0, 20], 'color': '#f1e05a'},
                                {'range': [20, 50], 'color': '#da3633'}]
                        }))
                    fig_gauge.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig_gauge, use_container_width=True, key=f"g_{symbol}_{i}")
                    
                    # --- SMART SUMMARY 1 ---
                    risk_lvl = "High" if risk_val > 20 else "Moderate" if risk_val > 0 else "Low"
                    st.markdown(f"""<div class="risk-card">
                        <b>Risk Analysis:</b> {symbol} มีความเสี่ยงต่อการเปลี่ยนผ่านในระดับ <b>{risk_lvl}</b> 
                        ภายใต้เงื่อนไข {scenario}. ค่า Carbon Beta ที่ปรับปรุงแล้วเท่ากับ <b>{risk_val:.2f}</b>
                        </div>""", unsafe_allow_html=True)

                with c2:
                    st.subheader("💰 Equity Value Bridge (MB)")
                    # VALUATION WATERFALL
                    m_cap = d['info'].get('marketCap', 1e11)
                    mkt_cap_mb = float(m_cap)/1e6
                    val_impact = (tax_price * 1000) / wacc_val / 1e6
                    adj_val = mkt_cap_mb - val_impact
                    
                    fig_water = go.Figure(go.Waterfall(
                        orientation = "v", measure = ["relative", "relative", "total"],
                        x = ["Initial Cap", "Climate Loss", "Adj. Value"],
                        y = [mkt_cap_mb, -val_impact, adj_val],
                        text = [f"{mkt_cap_mb:,.0f}", f"-{val_impact:,.0f}", f"{adj_val:,.0f}"],
                        textposition = "outside",
                        increasing = {"marker":{"color":"#2ea043"}},
                        decreasing = {"marker":{"color":"#da3633"}},
                        totals = {"marker":{"color":"#1f6feb"}}
                    ))
                    fig_water.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig_water, use_container_width=True, key=f"w_{symbol}_{i}")
                    
                    # --- SMART SUMMARY 2 ---
                    st.markdown(f"""<div class="insight-card">
                        <b>Valuation Analysis:</b> มูลค่ากิจการอาจถูกปรับลดลง <b>-{val_impact:,.2f} MB</b> 
                        (คิดเป็น <b>-{ (val_impact/mkt_cap_mb)*100:.2f}%</b>) หากมีการบังคับใช้ภาษีคาร์บอนเต็มรูปแบบ
                        </div>""", unsafe_allow_html=True)

                st.divider()
                # Bottom Section: Momentum & Recovery Insights
                m1, m2 = st.columns([1.5, 1])
                with m1:
                    st.subheader("📈 Price Momentum (3Y)")
                    st.line_chart(d['history'], height=300)
                with m2:
                    st.subheader("📰 Combined Insights")
                    # RECOVERY SYSTEM: หากข่าวว่าง ให้ใช้บทวิเคราะห์แทน
                    if d['news']:
                        for n in d['news']:
                            st.write(f"**{n.get('publisher','Market')}**: {n.get('title','Latest Climate Update')}")
                            st.divider()
                    else:
                        st.info(f"📊 **Climate Insight for {symbol}:**")
                        st.write(f"- ตลาดมีความอ่อนไหวต่อราคาคาร์บอนอยู่ที่ {d['c_beta']:.4f}")
                        st.write(f"- ความเสี่ยงทางกายภาพ (Flood) ในพื้นที่ตั้งอยู่ที่ {flood_exp}%")
                        st.caption("ข้อมูลข่าวสารจะอัปเดตอัตโนมัติเมื่อระบบ API พร้อมใช้งาน")

# --- FOOTER: PRESENTED BY RUN CHANTRAPIPAT ---
st.markdown("""
    <div class="footer">
        🏛️ Sustainable Finance Research Terminal | <b>Presented by Run Chantrapipat</b> | © 2026
    </div>
    """, unsafe_allow_html=True)
