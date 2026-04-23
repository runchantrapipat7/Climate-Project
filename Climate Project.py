import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Climate Finance Intelligence Pro", layout="wide")

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
        background: rgba(0, 255, 136, 0.05);
        border-left: 4px solid #00ff88;
        padding: 15px; border-radius: 8px; margin-top: 10px;
    }
    .risk-card {
        background: rgba(255, 75, 75, 0.05);
        border-left: 4px solid #ff4b4b;
        padding: 15px; border-radius: 8px; margin-top: 10px;
    }
    div[data-testid="stMetricValue"] > div { color: #00ff88 !important; font-size: 24px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background: linear-gradient(90deg, #2ea043, #238636) !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: ALL FEATURES PRESERVED ---
with st.sidebar:
    st.title("🛡️ Risk Terminal")
    st.header("🔍 ระบุชื่อหุ้นหรือกองทุน (Stock or Bond)")
    t1 = st.text_input("Asset 1", "PTT.BK")
    t2 = st.text_input("Asset 2", "EA.BK")
    t3 = st.text_input("Asset 3", "")
    tickers = [t.strip().upper() for t in [t1, t2, t3] if t.strip()]

    st.divider()
    st.header("🌍 Scenario & Policy (TCFD)")
    scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
    tax_multiplier = {"Net Zero 2050": 1.5, "Delayed Transition": 1.0, "Current Policy": 0.5}[scenario]
    tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    flood_risk = st.slider("Flood Exposure (%)", 0, 100, 45)
    wacc = st.slider("WACC (%)", 5.0, 15.0, 8.0) / 100

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
    analysis = fetch_pro_data(tickers)
    if analysis:
        # Comparative Overview Cards
        cols = st.columns(len(analysis))
        for i, (symbol, d) in enumerate(analysis.items()):
            cols[i].metric(f"💎 {symbol}", f"{d['price']:,.2f}", delta=f"C-Beta: {d['c_beta']:.3f}")

        # Deep Dive Analysis Tabs
        tabs = st.tabs([f"Intelligence Center: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                c1, c2 = st.columns(2)
                
                with c1:
                    st.subheader("🔥 Transition Risk Sensitivity")
                    # DYNAMIC GAUGE
                    risk_score = d['c_beta'] * 100 * tax_multiplier
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number", value = risk_score,
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
                    
                    # --- SUMMARY BOX 1 ---
                    risk_status = "High Risk" if risk_score > 20 else "Moderate" if risk_score > 0 else "Low Risk"
                    st.markdown(f"""<div class="risk-card">
                        <b>Transition Insight:</b> {symbol} มีความเสี่ยงระดับ <b>{risk_status}</b> 
                        ภายใต้เงื่อนไข {scenario}. ค่า Carbon Beta ที่ปรับปรุงแล้วคือ <b>{risk_score:.2f}</b>
                        </div>""", unsafe_allow_html=True)

                with c2:
                    st.subheader("💰 Equity Value Bridge (MB)")
                    # PREMIUM WATERFALL
                    m_cap = d['info'].get('marketCap', 1e11)
                    mkt_cap_mb = float(m_cap)/1e6
                    val_impact = (tax_price * 1000) / wacc / 1e6
                    adj_val = mkt_cap_mb - val_impact
                    
                    fig_water = go.Figure(go.Waterfall(
                        orientation = "v",
                        measure = ["relative", "relative", "total"],
                        x = ["Starting Cap", "Climate Loss", "Adj. Value"],
                        y = [mkt_cap_mb, -val_impact, adj_val],
                        text = [f"{mkt_cap_mb:,.0f}", f"-{val_impact:,.0f}", f"{adj_val:,.0f}"],
                        textposition = "outside",
                        increasing = {"marker":{"color":"#2ea043"}},
                        decreasing = {"marker":{"color":"#da3633"}},
                        totals = {"marker":{"color":"#1f6feb"}}
                    ))
                    fig_water.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig_water, use_container_width=True, key=f"w_{symbol}_{i}")
                    
                    # --- SUMMARY BOX 2 ---
                    st.markdown(f"""<div class="insight-card">
                        <b>Valuation Insight:</b> มูลค่ากิจการอาจลดลง <b>-{val_impact:,.2f} MB</b> 
                        หรือคิดเป็น <b>-{(val_impact/mkt_cap_mb)*100:.2f}%</b> จากผลกระทบของนโยบายคาร์บอน
                        </div>""", unsafe_allow_html=True)

                st.divider()
                # Bottom Section: Momentum & News (Preserved)
                m1, m2 = st.columns([1.5, 1])
                with m1:
                    st.subheader("📈 Price Momentum (3Y)")
                    st.line_chart(d['history'], height=250)
                with m2:
                    st.subheader("📰 Combined Insights")
                    if d['news']:
                        for n in d['news']:
                            st.write(f"**{n.get('publisher','Source')}**: {n.get('title','No Title')}")
                            st.divider()
                    else: st.info(f"No recent news. Beta is {d['c_beta']:.4f}")
