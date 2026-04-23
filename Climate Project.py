import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Climate Comparison Suite", layout="wide")

# --- CSS: Dashboard Style ---
st.markdown("""
    <style>
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px; border-radius: 12px;
    }
    .stMultiSelect div[data-baseweb="select"] { background-color: #1e1e1e; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚖️ Comparison Engine")
    # เปลี่ยนเป็น Multi-select หรือ Input ที่รองรับหลายตัว
    tickers_raw = st.text_input("ระบุ Ticker ที่ต้องการเปรียบเทียบ (แยกด้วยคอมม่า เช่น PTT.BK, SCC.BK, EA.BK)", "PTT.BK, SCC.BK")
    tickers = [t.strip().upper() for t in tickers_raw.split(",")]
    
    st.divider()
    st.header("🌍 Scenario & Policy")
    scenario = st.select_slider("Climate Ambition", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
    tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    
    st.divider()
    st.header("🌊 Physical Risk Score")
    flood_risk = st.slider("Flood Exposure (%)", 0, 100, 45)
    wacc = st.slider("WACC (%)", 5.0, 15.0, 8.0) / 100

# --- CORE LOGIC: BATCH DATA ENGINE ---
@st.cache_data(ttl=3600)
def fetch_comparison_data(ticker_list):
    try:
        # ดึงข้อมูลหุ้นทั้งหมด + Proxy
        all_tickers = ticker_list + ["PTTEP.BK", "EA.BK", "^SET.BK"]
        data = yf.download(all_tickers, start="2023-01-01", progress=False)['Close']
        returns = data.pct_change().dropna()
        
        results = []
        for symbol in ticker_list:
            if symbol in returns.columns:
                # คำนวณ Carbon Beta สำหรับแต่ละตัว
                bmg = returns["PTTEP.BK"] - returns["EA.BK"]
                X = sm.add_constant(pd.DataFrame({'Market': returns["^SET.BK"], 'Carbon': bmg}))
                model = sm.OLS(returns[symbol], X).fit()
                
                results.append({
                    "Ticker": symbol,
                    "Carbon_Beta": model.params['Carbon'],
                    "Market_Beta": model.params['Market'],
                    "Last_Price": data[symbol].iloc[-1],
                    "Cumulative_Return": (returns[symbol] + 1).prod() - 1
                })
        return pd.DataFrame(results), data[ticker_list]
    except: return None, None

# --- MAIN DISPLAY ---
st.title("⚖️ Climate Risk & Sustainable Finance: Comparative Suite")
st.markdown(f"**Analytics Terminal** | Comparing {len(tickers)} assets | {datetime.now().strftime('%d %Y')}")

if len(tickers) > 0:
    res_df, price_history = fetch_comparison_data(tickers)
    
    if res_df is not None and not res_df.empty:
        # --- ROW 1: COMPARATIVE METRICS TABLE ---
        st.subheader("📊 Comparative Summary Table")
        # คำนวณความเสียหายจากคาร์บอน (Simulation: ทุก 1M ตัน)
        res_df['Est_Valuation_Loss_MB'] = (1000000 * tax_price / wacc) / 1e6
        
        # แสดงตารางสวยๆ
        st.dataframe(res_df.style.background_gradient(subset=['Carbon_Beta'], cmap='RdYlGn_r'), use_container_width=True)

        st.divider()

        # --- ROW 2: VISUAL COMPARISON ---
        col_l, col_r = st.columns(2)
        
        with col_l:
            st.subheader("📉 Price Performance Comparison")
            # กราฟราคา Normalize
            normalized_prices = (price_history / price_history.iloc[0]) * 100
            fig_perf = px.line(normalized_prices, title="Relative Performance (Base 100)")
            st.plotly_chart(fig_perf, use_container_width=True)

        with col_r:
            st.subheader("🔥 Carbon Risk vs. Cumulative Return")
            # กราฟ Scatter วิเคราะห์ความเสี่ยง
            fig_scatter = px.scatter(res_df, x="Carbon_Beta", y="Cumulative_Return", 
                                     text="Ticker", size=np.abs(res_df["Carbon_Beta"])*100,
                                     color="Carbon_Beta", color_continuous_scale='RdYlGn_r',
                                     title="Climate Risk Exposure Mapping")
            fig_scatter.add_vline(x=0, line_dash="dash", line_color="white")
            st.plotly_chart(fig_scatter, use_container_width=True)
            st.caption("โซนซ้าย (สีเขียว): ได้ประโยชน์จากการเปลี่ยนผ่าน | โซนขวา (สีแดง): เสี่ยงต่อภาษีคาร์บอน")

        # --- ROW 3: DEEP INSIGHTS ---
        st.divider()
        st.subheader("🧬 Sustainable Finance Insights")
        
        best_stock = res_df.loc[res_df['Carbon_Beta'].idxmin()]
        worst_stock = res_df.loc[res_df['Carbon_Beta'].idxmax()]
        
        c1, c2 = st.columns(2)
        with c1:
            st.success(f"**Most Climate Resilient:** {best_stock['Ticker']}")
            st.write(f"มีความอ่อนไหวต่อราคาคาร์บอนต่ำที่สุด ({best_stock['Carbon_Beta']:.3f}) เหมาะสำหรับพอร์ตความยั่งยืน")
        
        with c2:
            st.error(f"**Highest Transition Risk:** {worst_stock['Ticker']}")
            st.write(f"มีความอ่อนไหวต่อราคาคาร์บอนสูงสุด ({worst_stock['Carbon_Beta']:.3f}) อาจต้องตั้งสำรองภาษีเพิ่มขึ้น {worst_stock['Est_Valuation_Loss_MB']:,.0f} MB ต่อล้านตันคาร์บอน")

        # --- NEWS FOR ALL TICKERS ---
        st.divider()
        st.subheader("📰 Combined Research Intelligence")
        for t in tickers:
            with st.expander(f"Latest Intelligence for {t}"):
                try:
                    news = yf.Ticker(t).news[:3]
                    for n in news:
                        st.write(f"**[{n.get('publisher', 'N/A')}]** - {n.get('title', 'N/A')}")
                        st.write(f"[Read full article]({n.get('link', '#')})")
                        st.divider()
                except: st.write("ไม่สามารถดึงข้อมูลข่าวสารได้")

    else:
        st.error("ไม่สามารถดึงข้อมูลได้ กรุณาตรวจสอบว่าชื่อหุ้นถูกต้องและแยกด้วยเครื่องหมายคอมม่า (เช่น PTT.BK, EA.BK)")
