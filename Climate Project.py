import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Sustainable Finance Analyzer", layout="wide")

# --- CSS: Modern Dashboard ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        padding: 20px; border-radius: 15px;
    }
    div[data-testid="stMetricValue"] > div { color: #2ECC71 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { 
        height: 50px; background-color: rgba(255, 255, 255, 0.05); 
        border-radius: 10px 10px 0 0; padding: 10px 20px; color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚖️ Portfolio Intelligence")
    st.write("ระบุหุ้น/กองทุน (แยกช่องละ 1 ตัว)")
    t1 = st.text_input("Asset 1", "PTT.BK")
    t2 = st.text_input("Asset 2", "BTS.BK")
    t3 = st.text_input("Asset 3", "")
    tickers = [t.strip().upper() for t in [t1, t2, t3] if t.strip()]

    st.divider()
    st.header("🌍 Scenario & Policy (TCFD)")
    scenario = st.select_slider("Ambition Level", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
    tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    st.divider()
    st.header("🌊 Physical Risk Control")
    flood_risk = st.slider("Flood Exposure (%)", 0, 100, 45)
    wacc = st.slider("WACC (%)", 5.0, 15.0, 8.0) / 100

# --- DATA ENGINE (REBUILT FOR STABILITY) ---
@st.cache_data(ttl=600) # ลดเวลา Cache เพื่อให้ข้อมูลสดใหม่เสมอ
def fetch_robust_data(ticker_list):
    full_res = {}
    combined_prices = pd.DataFrame()
    
    # ดึงข้อมูล Proxy แยกต่างหากเพื่อความปลอดภัย
    try:
        proxies = yf.download(["PTTEP.BK", "EA.BK", "^SET.BK"], period="5y", progress=False)['Close']
        proxies = proxies.ffill().bfill()
    except:
        proxies = pd.DataFrame()

    for symbol in ticker_list:
        try:
            # ดึงข้อมูลหุ้นรายตัว
            ticker_data = yf.download(symbol, period="5y", progress=False)['Close']
            if ticker_data.empty: continue
            
            ticker_data = ticker_data.to_frame(name=symbol)
            combined_prices = pd.concat([combined_prices, ticker_data], axis=1)
            
            t_obj = yf.Ticker(symbol)
            
            # คำนวณ Carbon Beta (ถ้ามีข้อมูล Proxy ครบ)
            c_beta, m_beta = 0.0, 1.0
            if not proxies.empty:
                try:
                    temp_df = pd.concat([ticker_data, proxies], axis=1).pct_change().dropna()
                    bmg = temp_df["PTTEP.BK"] - temp_df["EA.BK"]
                    X = sm.add_constant(pd.DataFrame({'Market': temp_df["^SET.BK"], 'Carbon': bmg}))
                    model = sm.OLS(temp_df[symbol], X).fit()
                    c_beta, m_beta = model.params['Carbon'], model.params['Market']
                except: pass

            full_res[symbol] = {
                "last_price": ticker_data[symbol].dropna().iloc[-1],
                "history": ticker_data[symbol],
                "carbon_beta": c_beta,
                "market_beta": m_beta,
                "info": t_obj.info,
                "news": t_obj.news[:5]
            }
        except: continue
        
    return full_res, combined_prices

# --- MAIN DISPLAY ---
st.title("🏛️ Sustainable Finance & Climate Risk Intelligence")
st.markdown(f"**Market Intelligence Terminal** | {datetime.now().strftime('%d %B %Y')}")

if tickers:
    analysis, history = fetch_robust_data(tickers)
    
    if analysis:
        # Overview Cards
        cols = st.columns(len(analysis))
        for i, (symbol, d) in enumerate(analysis.items()):
            cols[i].metric(f"💎 {symbol}", f"{d['last_price']:,.2f}", delta=f"C-Beta: {d['carbon_beta']:.3f}")

        # Deep Dive Tabs
        tabs = st.tabs([f"Asset: {s}" for s in analysis.keys()])
        for i, (symbol, d) in enumerate(analysis.items()):
            with tabs[i]:
                # ข้อมูลหุ้นยังอยู่ครบถ้วน
                f1, f2, f3, f4 = st.columns(4)
                f1.metric("P/E Ratio", d['info'].get('trailingPE', 'N/A'))
                f2.metric("Div. Yield", f"{d['info'].get('dividendYield', 0)*100:.2f}%")
                f3.metric("Market Cap", f"{d['info'].get('marketCap', 0)/1e9:.1f}B")
                f4.metric("Market Beta", f"{d['market_beta']:.2f}")

                # Charts
                c_l, c_r = st.columns([2, 1])
                with c_l:
                    st.subheader("📈 Price Momentum")
                    st.line_chart(d['history'])
                with c_r:
                    st.subheader("🔥 Carbon Sensitivity")
                    fig_gauge = go.Figure(go.Indicator(
                        mode = "gauge+number", value = d['carbon_beta'] * 100,
                        gauge = {'axis': {'range': [-50, 50]}, 'bar': {'color': "#E74C3C" if d['carbon_beta'] > 0 else "#2ECC71"}}))
                    fig_gauge.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                    st.plotly_chart(fig_gauge, use_container_width=True)

                # Waterfall (Fixed ValueError)
                st.divider()
                st.subheader("💰 Equity Value Bridge (MB)")
                mkt_cap_mb = float(d['info'].get('marketCap', 1e9))/1e6
                val_impact = (tax_price * 1000) / wacc / 1e6
                
                fig_water = go.Figure(go.Waterfall(
                    orientation = "v", x = ["Current Cap", "Climate Loss", "Adjusted Value"],
                    y = [mkt_cap_mb, -val_impact, mkt_cap_mb - val_impact],
                    measure = ["relative", "relative", "total"],
                    decreasing = {"marker":{"color":"#E74C3C"}},
                    total = {"marker":{"color":"#3498DB"}}
                ))
                fig_water.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
                st.plotly_chart(fig_water, use_container_width=True)
                
                # News
                st.subheader("📰 Latest News")
                for n in d['news']:
                    st.write(f"**[{n.get('publisher','N/A')}]** {n.get('title','N/A')}")
                    st.divider()

        # Overall Comparative Momentum
        st.divider()
        st.subheader("📉 Normalized Momentum Comparison")
        if not history.empty:
            norm_prices = (history / history.iloc[0]) * 100
            st.line_chart(norm_prices)

    else: st.error("❌ ไม่พบข้อมูล Ticker ที่ระบุ กรุณาลองใหม่อีกครั้ง หรือตรวจสอบตัวสะกด (เช่น PTT.BK)")
