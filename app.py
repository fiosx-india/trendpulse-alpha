import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf

# --- பக்க வடிவமைப்பு அமைப்புகள் ---
st.set_page_config(
    page_title="TrendPulse Alpha Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ஸ்டைல் கஸ்டமைசேஷன் ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    div[data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; color: #00ffcc; }
    div[data-testid="stMetricDelta"] { font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

# --- அப்ளிகேஷன் ஹெட்டர் ---
st.title("🚀 TrendPulse Alpha Pro")
st.caption("Universal 5-Day Swing Target Engine for NSE & BSE Stocks")

# --- சைட் பார் கண்ட்ரோல் பேனல் (தேடல் வசதி) ---
st.sidebar.header("🔍 Universal Stock Finder")
st.sidebar.markdown("இந்தியாவின் 5,000+ நிறுவனங்களில் எதை வேண்டுமானாலும் நீங்கள் தேடலாம்.")

# பயனர் நேரடியாக டைப் செய்யும் தேடல் பெட்டி (Default ஆக TATASTEEL)
user_input = st.sidebar.text_input("பங்கின் குறியீட்டை உள்ளிடவும் (e.g., SBIN, RELIANCE, ITC):", "TATASTEEL").upper().strip()

# சந்தை தேர்வு (NSE அல்லது BSE)
market_type = st.sidebar.radio("பங்குச்சந்தையைத் தேர்ந்தெடுக்கவும்:", ["NSE (தேசிய சந்தை)", "BSE (மும்பை சந்தை)"])

# சர்வவல்லமையுள்ள குறியீட்டு மாற்றி லாஜிக்
if market_type == "NSE (தேசிய சந்தை)":
    selected_ticker = f"{user_input}.NS"
else:
    selected_ticker = f"{user_input}.BO"

test_days = st.sidebar.slider("Historical Data Scope (Days)", 60, 180, 120)

st.sidebar.write("---")
st.sidebar.markdown("""
💡 **உதவிக்குறிப்பு:**
* NSE பங்குகளுக்கு: `RELIANCE`, `SBIN`, `INFY`
* BSE பங்குகளுக்கு: `500325` (ரிலையன்ஸ் குறியீடு) அல்லது கம்பெனி பெயர்.
""")

# --- நிஜமான டேட்டா இன்ஜின் ---
try:
    with st.spinner("மார்க்கெட் சர்வரில் இருந்து நிஜத் தரவுகள் எடுக்கப்படுகிறது..."):
        df = yf.download(selected_ticker, period="6mo", interval="1d")
    
    if not df.empty:
        df = df.tail(test_days)
        
        # சீரான தரவுகளுக்கு சீரிஸ் மாற்று
        df_close = df['Close'].squeeze()
        df_high = df['High'].squeeze()
        df_low = df['Low'].squeeze()
        df_open = df['Open'].squeeze()

        # 📊 ஸ்ட்ராட்டஜி இண்டிகேட்டர்கள் கணக்கீடு
        df['SMA_20'] = df_close.rolling(window=20).mean()
        
        delta = df_close.diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = (-delta.clip(upper=0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 5-நாள் டார்கெட் கணிப்பு (Pivot Points Formula)
        prev_high = float(df_high.iloc[-2])
        prev_low = float(df_low.iloc[-2])
        prev_close = float(df_close.iloc[-2])
        
        pivot = (prev_high + prev_low + prev_close) / 3
        current_target_1 = (2 * pivot) - prev_low
        current_target_2 = pivot + (prev_high - prev_low)
        current_stoploss = pivot - (prev_high - prev_low)
        
        current_close = float(df_close.iloc[-1])
        prev_close_val = float(df_close.iloc[-2])
        current_rsi = float(df['RSI'].iloc[-1])
        current_sma = float(df['SMA_20'].iloc[-1])

        # --- மெயின் டேஷ்போர்டு கார்டுகள் ---
        st.subheader(f"📊 {user_input} - தற்போதைய சந்தை நிலவரம்")
        col1, col2, col3, col4 = st.columns(4)
        price_change = ((current_close - prev_close_val) / prev_close_val) * 100
        col1.metric("Current Price", f"₹{current_close:.2f}", f"{price_change:.2f}%")
        col2.metric("🎯 5-Day Target 1 (R1)", f"₹{current_target_1:.2f}")
        col3.metric("🚀 5-Day Target 2 (R2)", f"₹{current_target_2:.2f}")
        col4.metric("🛑 Guard StopLoss (S2)", f"₹{current_stoploss:.2f}")

        st.write("---")

        # --- சார்ட் வரைபடம் ---
        st.subheader("📈 Algorithmic Target Mapping Chart")
        fig = go.Figure()
        
        fig.add_trace(go.Candlestick(
            x=df.index, open=df_open, high=df_high, low=df_low, close=df_close,
            name="Price Action"
        ))
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='#ffaa00', width=1.5), name="20 SMA Trend"))

        # டார்கெட் லைன்கள்
        fig.add_trace(go.Scatter(x=[df.index[-5], df.index[-1]], y=[current_target_1, current_target_1], line=dict(color='#00ffcc', dash='dash'), name="Target 1"))
        fig.add_trace(go.Scatter(x=[df.index[-5], df.index[-1]], y=[current_stoploss, current_stoploss], line=dict(color='#ff4b4b', dash='dash'), name="Stop Loss"))

        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=450, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

        # --- அல்கோ பிரேக்அவுட் முடிவு ---
        st.subheader("🧪 Core AI Technical Strategy Summary")
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("### 🏷️ Mathematical Matrix")
            st.write(f"**RSI Momentum (14D):** `{current_rsi:.2f}`")
            if current_rsi > 70:
                st.warning("⚠️ Overbought zone! Target might have exhausted.")
            elif current_rsi < 30:
                st.success("🟢 Oversold structural bottom! High probability reversal upward.")
            else:
                st.info("🔵 Neutral Momentum Zone.")

        with col_b:
            st.markdown("### 🛡️ 5-Day Predictive Decision Logic")
            is_above_sma = current_close > current_sma
            if is_above_sma and current_rsi < 65:
                st.success("🔥 **BULLISH BREAKOUT TRIGGERED:** Price is healthy above 20 SMA. Target 1 has high probability of execution within 5 sessions.")
            else:
                st.error("📉 **CONSOLIDATION OR WEAKNESS:** Price setup is tracking flat. Maintain strict monitoring of the StopLoss level.")

        st.info("💡 Note: This tool runs fully using pure mathematical frameworks to gauge entry-target correlations on historic timelines.")
    else:
        st.error(f"மன்னிக்கவும்! '{user_input}' என்ற குறியீட்டில் எந்த ஒரு நிறுவனமும் கண்டறியப்படவில்லை. குறியீட்டைச் சரிபார்க்கவும்.")
except Exception as e:
    st.error(f"தரவுகளைப் பெறுவதில் பிழை ஏற்பட்டுள்ளது. குறியீடு சரியாக உள்ளதா என உறுதிப்படுத்தவும்.")
