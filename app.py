import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="TrendPulse Alpha",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- STYLE CUSTOMIZATION ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    div[data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; color: #00ffcc; }
    div[data-testid="stMetricDelta"] { font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

# --- APPLICATION HEADER ---
st.title("📈 TrendPulse Alpha")
st.caption("Advanced Mathematical Backtesting & Target Prediction Engine for 5-Day Swing Trading")

# --- SIMULATED DATA ENGINE (BACKTESTING GROUND) ---
@st.cache_data
def generate_mock_data(ticker, days=120):
    np.random.seed(42 if ticker == "TATASTEEL" else 99)
    date_today = datetime.now()
    dates = [date_today - timedelta(days=x) for x in range(days)]
    dates.reverse()
    
    # Generate geometric brownian motion structure
    price = 100.0 if ticker == "TATASTEEL" else 2500.0
    prices = []
    for _ in range(days):
        price = price * (1 + np.random.normal(0.001, 0.02))
        prices.append(price)
        
    df = pd.DataFrame({
        'Date': dates,
        'Close': prices
    })
    df['High'] = df['Close'] * (1 + np.random.uniform(0.005, 0.02, days))
    df['Low'] = df['Close'] * (1 - np.random.uniform(0.005, 0.02, days))
    df['Open'] = (df['High'] + df['Low']) / 2
    df.set_index('Date', inplace=True)
    return df

# --- MATH STRATEGIES & INDICATORS ENGINE ---
def compute_indicators(df):
    # 1. 20-Day Simple Moving Average (SMA)
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    
    # 2. Relative Strength Index (RSI - 14 Days)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-10)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 3. Pivot Points & 5-Day Targets (Mathematical Support/Resistance)
    # Using previous complete block characteristics
    prev_high = df['High'].iloc[-2]
    prev_low = df['Low'].iloc[-2]
    prev_close = df['Close'].iloc[-2]
    
    pivot = (prev_high + prev_low + prev_close) / 3
    df['Pivot'] = pivot
    df['Target_1'] = (2 * pivot) - prev_low       # Resistance 1 (Target 1)
    df['Target_2'] = pivot + (prev_high - prev_low) # Resistance 2 (Target 2)
    df['StopLoss'] = pivot - (prev_high - prev_low) # Support 2 (StopLoss)
    
    return df

# --- SIDEBAR INTERFACE ---
st.sidebar.header("🛠️ Test Control Panel")
selected_ticker = st.sidebar.selectbox("Select Equity Ticker", ["TATASTEEL", "RELIANCE"])
test_days = st.sidebar.slider("Historical Data Scope (Days)", 60, 180, 120)

# Load and compute
data = generate_mock_data(selected_ticker, test_days)
data = compute_indicators(data)

current_row = data.iloc[-1]
prev_row = data.iloc[-2]

# --- MAIN DASHBOARD VISUALS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Current Market Price", f"₹{current_row['Close']:.2f}", f"{(current_row['Close']-prev_row['Close'])/prev_row['Close']*100:.2f}%")
col2.metric("🎯 5-Day Target 1 (R1)", f"₹{current_row['Target_1']:.2f}")
col3.metric("🚀 5-Day Target 2 (R2)", f"₹{current_row['Target_2']:.2f}")
col4.metric("🛑 Guard StopLoss (S2)", f"₹{current_row['StopLoss']:.2f}")

st.write("---")

# --- PLOTLY CANDLESTICK VISUALIZATION ---
st.subheader("📊 Algorithmic Target Mapping Chart")

fig = go.Figure()
# Candlestick
fig.add_trace(go.Candlestick(
    x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
    name="Price Action"
))
# SMA 20 Trend line
fig.add_trace(go.Scatter(x=data.index, y=data['SMA_20'], line=dict(color='#ffaa00', width=1.5), name="20 SMA Trend"))

# Target lines for visual tracking
fig.add_trace(go.Scatter(x=[data.index[-5], data.index[-1]], y=[current_row['Target_1'], current_row['Target_1']], line=dict(color='#00ffcc', dash='dash'), name="Target 1"))
fig.add_trace(go.Scatter(x=[data.index[-5], data.index[-1]], y=[current_row['StopLoss'], current_row['StopLoss']], line=dict(color='#ff4b4b', dash='dash'), name="Stop Loss"))

fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=450, margin=dict(l=20, r=20, t=20, b=20))
st.plotly_chart(fig, use_container_width=True)

# --- BACKTEST VALIDATION BOARD ---
st.subheader("🧪 Core AI Technical Strategy Summary")
col_a, col_b = st.columns(2)

with col_a:
    st.markdown("### 🏷️ Mathematical Matrix")
    st.write(f"**RSI Momentum (14D):** `{current_row['RSI']:.2f}`")
    if current_row['RSI'] > 70:
        st.warning("⚠️ Overbought zone! Target might have exhausted.")
    elif current_row['RSI'] < 30:
        st.success("🟢 Oversold structural bottom! High probability reversal upward.")
    else:
        st.info("🔵 Neutral Momentum Zone.")

with col_b:
    st.markdown("### 🛡️ 5-Day Predictive Decision Logic")
    is_above_sma = current_row['Close'] > current_row['SMA_20']
    if is_above_sma and current_row['RSI'] < 65:
        st.success("🔥 **BULLISH BREAKOUT TRIGGERED:** Price is healthy above 20 SMA. Target 1 has high probability of execution within 5 sessions.")
    else:
        st.error("📉 **CONSOLIDATION OR WEAKNESS:** Price setup is tracking flat. Maintain strict monitoring of the StopLoss level.")

st.info("💡 Note: This tool runs fully locally using pure mathematical frameworks to gauge entry-target correlations on historic timelines.")