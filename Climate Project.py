import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import statsmodels.api as sm
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Climate Risk Comparison", layout="wide")

# --- CSS: Professional Theme ---
st.markdown("""
    <style>
    div[data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(128, 128, 128, 0.1);
        padding: 15px; border-radius: 12px;
    }
    [data-testid="stMetricValue"] > div { color: #2ECC71 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: MULTI-INPUT ---
with st.sidebar:
    st.title("⚖️ Asset Comparison")
    st.write("ระบุชื่อหุ้นที่ต้องการเปรียบเทียบ (2-3 ตัว)")
    t1 = st.text_input("หุ้นตัวที่ 1", "PTT.BK")
    t2 = st.text_input("หุ้นตัวที่ 2", "SCC.BK")
    t3 = st.text_input("หุ้นตัวที่ 3 (ไม่ใส่ก็ได้)", "")
    
    # รวบรวม Ticker ที่ไม่ว่าง
    tickers = [t.strip().upper() for t in [t1, t2, t3] if t.strip()]

    st.divider()
    st.header("🌍 Scenario & Policy")
    scenario = st.select_slider("Policy Ambition", options=["Net Zero 2050", "Delayed Transition", "Current Policy"])
    tax_price = {"Net Zero 2050": 1500, "Delayed Transition": 800, "Current Policy": 200}[scenario]
    wacc = st.slider("WACC (%)", 5.0, 15.0, 8.0) / 100

# --- CORE LOGIC: COMPREHENSIVE ENGINE ---
@st.cache_data(ttl=3600)
def analyze_assets(ticker_list):
    try:
        # ดึงข้อมูลหุ้นทั้งหมด + ดัชนีตัวแทน (Brown/Green/Market)
        all_to_fetch = ticker_list + ["PTTEP.BK", "EA.BK", "^SET.BK"]
        data = yf.download(all_to_fetch, start="2023-01-01", progress=False)['Close']
        returns = data.pct_change().dropna()
        
        results = []
        for symbol in ticker_list:
            if symbol in returns.columns:
                # คำนวณ Carbon Beta
                bmg = returns["PTTEP.BK"] - returns["EA.BK"]
                X = sm.add_constant(pd.DataFrame({'Market': returns["^SET.BK"], 'Carbon': bmg}))
                model = sm.OLS(returns[symbol], X).fit()
                
                # ดึงข่าว (ใช้ Try เพื่อไม่ให้พังถ้าหาข่าวไม่เจอ)
                try: news = yf.Ticker(symbol).news[:2]
                except: news = []
                
                results.append({
                    "Ticker": symbol,
                    "Price": data[symbol].iloc[-1],
                    "Carbon_Beta": model.params['Carbon'],
                    "Market_Beta": model.params['Market'],
                    "Return": (returns[symbol] + 1).prod() - 1,
                    "News": news
                })
        return results, data[ticker_list]
    except: return None, None

# --- MAIN DASHBOARD ---
st.title("🏛️ Climate Risk Modeling & Sustainable Finance")
st.markdown(f"**Asset Comparison Portal** | Analysis Date: {datetime.now().strftime('%d %B %Y')}")

if tickers:
    res_list, price_hist = analyze_assets(tickers)
    
    if res_list:
        # --- ROW 1: COMPARATIVE CARDS ---
        cols = st.columns(len(res_list))
        for i, item in enumerate(res_list):
            with cols[i]:
                st.subheader(f"💎 {item['Ticker']}")
                st.metric("Price", f"{item['Price']:.2f} THB")
                st.metric("Carbon Beta", f"{item['Carbon_Beta']:.3f}")
                st.caption("Lower is better for Transition Risk")

        st.divider()

        # --- ROW 2: VISUAL ANALYTICS ---
        c_left, c_right = st.columns([1.5, 1])
        
        with c_left:
            st.subheader("📈 Performance Comparison (Relative)")
            norm_prices = (price_hist / price_hist.iloc[0]) * 100
            st.line_chart(norm_prices)

        with c_right:
            st.subheader("🌡️ Risk Mapping")
            df_plot = pd.DataFrame(res_list)
            fig_scatter = px.scatter(df_plot, x="Carbon_Beta", y="Return", text="Ticker", 
                                     color="Carbon_Beta", color_continuous_scale="RdYlGn_r",
                                     title="Risk-Return Profile")
            fig_scatter.add_vline(x=0, line_dash="dash")
            st.plotly_chart(fig_scatter, use_container_width=True)

        # --- ROW 3: RESEARCH MEMO & NEWS ---
        st.divider()
        st.subheader("🧬 Sustainable Finance Intelligence")
        
        for item in res_list:
            with st.expander(f"Deep Insight & News for {item['Ticker']}"):
                col_a, col_b = st.columns(2)
                with col_a:
                    val_loss = (tax_price * 1000) / wacc / 1e6
                    st.info(f"""
                    **Research Memo:**
                    - **Transition Risk:** ความอ่อนไหวต่อคาร์บอนอยู่ที่ {item['Carbon_Beta']:.3f}
                    - **Valuation Impact:** ภายใต้ฉากทัศน์ {scenario} คาดว่ามูลค่าจะลดลงประมาณ -{val_loss:,.2f} ล้านบาท
                    - **Physical Risk:** พื้นที่ลุ่มน้ำเจ้าพระยาเสี่ยงอุทกภัย (95% ของภัยในไทย)
                    """)
                with col_b:
                    if item['News']:
                        for n in item['News']:
                            st.write(f"**[{n.get('publisher','N/A')}]** - {n.get('title','N/A')}")
                            st.write(f"[Link]({n.get('link','#')})")
                    else: st.write("ไม่มีข่าวสารล่าสุด")
    else:
        st.error("ไม่สามารถดึงข้อมูลได้ กรุณาตรวจสอบชื่อ Ticker (ต้องมี .BK สำหรับหุ้นไทย)")
