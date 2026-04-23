import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="Sustainable Finance Intelligence", layout="wide")

# --- CSS: Modern Glassmorphism Theme ---
st.markdown("""
    <style>
    .main { background-color: #0b0e14; color: #e1e1e1; }
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 12px; padding: 15px;
    }
    div[data-testid="stMetricValue"] > div { color: #00d26a !important; font-size: 28px; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: rgba(255, 255, 255, 0.03); 
        border-radius: 8px 8px 0 0; padding: 10px 25px; color: #888;
    }
    .stTabs [aria-selected="true"] { background-color: rgba(0, 210, 106, 0.1); color: #00d26a !2important; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Portfolio Risk")
    st.header("🔍 ระบุชื่อหุ้นหรือกองทุน (Stock or Bond)")
    t1 = st.text_input("Asset 1", "PTT.BK")
    t2 = st.text_input("Asset 2", "EA.BK")
    t3 = st.text_input("Asset 3", "")
    tickers = [t.strip().upper() for t in [t1, t2, t3] if t.strip()]

    st.divider()
    st.header("🌍 Scenario & Policy")
    scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
    tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    flood_risk = st.slider("Flood Exposure (%)", 0, 100, 45)
    wacc = st.slider("WACC (%)", 5.0, 15.0, 8.0) / 100

# --- DATA ENGINE ---
@st.cache_data(ttl=600)
def fetch_terminal_data(ticker_list):
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
            
            c_beta, m_beta = 0.0, 1.0
            if not proxies.empty:
                try:
                    temp_df = pd.concat([hist, proxies], axis=1).pct_change().dropna()
                    bmg = temp_df["PTTEP.BK"] - temp_df["EA.BK"]
                    X = sm.add_constant(pd.DataFrame({'Market': temp_df["^SET.BK"], 'Carbon': bmg}))
                    model = sm.OLS(temp_df[symbol], X).fit()
                    c_beta, m_beta = model.params.get('Carbon', 0.0), model.params.get('Market', 1.0)
                except: pass

            full_res[symbol] = {
                "last_price": float(hist.iloc[-1]),
                "history": hist,
                "carbon_beta": c_beta,
                "market_beta": m_beta,
                "info": t_obj.info if t_obj.info else {},
                "news": t_obj.news[:5] if t_obj.news else []
            }
        except: continue
    return full_res

# --- MAIN DISPLAY ---
st.title("🏛️ Sustainable Finance & Climate Risk Modeling")
st.markdown(f"**Asset Intelligence Terminal** | Data as of: {datetime.now().strftime('%d %B %Y')}")

if tickers:
    analysis = fetch_terminal_data(tickers)
    
    if analysis:
        # Overview Comparative Cards
        cols = st.columns(len(analysis))
        for i, (symbol, d) in enumerate(analysis.items()):
            with cols[i]:
                st.metric(f"💎 {symbol}", f"{d['last_price']:,.2f}", 
                          delta=f"C-Beta: {d['carbon_beta']:.3f}", delta_color="inverse")

        # Deep Dive Tabs
        tabs = st.tabs([f"Intelligence: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                # Financial Intelligence Row
                f1, f2, f3, f4 = st.columns(4)
                f1.metric("Current Price", f"{d['last_price']:,.2f}")
                f2.metric("Market Beta", f"{d['market_beta']:.2f}")
                m_cap = d['info'].get('marketCap')
                f3.metric("Div. Yield", f"{d['info'].get('dividendYield', 0)*100:.2f}%" if d['info'].get('dividendYield') else "N/A")
                f4.metric("Market Cap", f"{m_cap/1e9:.1f}B" if m_cap else "N/A")

                st.divider()

                # Modern Charts Row (Fixed Duplicate ID)
                c_l, c_r = st.columns([1.2, 1])
                with c_l:
                    st.subheader("🔥 Transition Risk Sensitivity")
                    # MODERN GAUGE DESIGN
                    c_beta_scaled = d['carbon_beta'] * 100
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number", value = c_beta_scaled,
                        gauge = {
                            'axis': {'range': [-50, 50], 'tickwidth': 1, 'tickcolor': "#444"},
                            'bar': {'color': "#00d26a" if c_beta_scaled < 5 else "#f5a623" if c_beta_scaled < 15 else "#ff4b4b"},
                            'bgcolor': "rgba(0,0,0,0)",
                            'borderwidth': 2, 'bordercolor': "#333",
                            'steps': [
                                {'range': [-50, 5], 'color': 'rgba(0, 210, 106, 0.1)'},
                                {'range': [5, 15], 'color': 'rgba(245, 166, 35, 0.1)'},
                                {'range': [15, 50], 'color': 'rgba(255, 75, 75, 0.1)'}],
                        }))
                    fig_gauge.update_layout(height=350, margin=dict(l=30, r=30, t=50, b=20), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig_gauge, use_container_width=True, key=f"gauge_{symbol}") # Fixed Key

                with c_r:
                    st.subheader("💰 Equity Value Bridge (MB)")
                    # MODERN WATERFALL DESIGN
                    mkt_cap_mb = float(m_cap)/1e6 if m_cap else 1000.0
                    val_impact = (tax_price * 1000) / wacc / 1e6
                    
                    fig_water = go.Figure(go.Waterfall(
                        orientation = "v",
                        measure = ["relative", "relative", "total"],
                        x = ["Starting Market Cap", "Climate Risk Loss", "Adjusted Fair Value"],
                        y = [mkt_cap_mb, -val_impact, mkt_cap_mb - val_impact],
                        connector = {"line":{"color":"#444"}},
                        increasing = {"marker":{"color":"#00d26a"}},
                        decreasing = {"marker":{"color":"#ff4b4b"}},
                        totals = {"marker":{"color":"#007bff"}}
                    ))
                    fig_water.update_layout(height=350, margin=dict(l=10, r=10, t=50, b=20), paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_water, use_container_width=True, key=f"water_{symbol}") # Fixed Key

                st.divider()
                
                # Bottom Row: Momentum & News
                n_l, n_r = st.columns([2, 1])
                with n_l:
                    st.subheader("📈 Price Momentum")
                    st.line_chart(d['history'], height=300)
                with n_r:
                    st.subheader("📰 Latest Insights")
                    for n in d['news'][:3]:
                        st.write(f"**[{n.get('publisher','N/A')}]** {n.get('title','N/A')}")
                        st.caption(f"[อ่านต่อ]({n.get('link','#')})")
                        st.divider()
    else:
        st.error("❌ ไม่พบข้อมูล Ticker ที่ระบุ หรือ API ติดขัด กรุณารอสักครู่แล้วลองใหม่")
