import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor
import time

# --- பக்க வடிவமைப்பு அமைப்புகள் ---
st.set_page_config(
    page_title="TrendPulse Alpha Quantum Pro",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
    <style>
    .main { background-color: #0b0e14; color: #ffffff; }
    div[data-testid="stMetricValue"] { font-size: 22px; font-weight: bold; color: #00ffcc; }
    .stDataFrame { background-color: #111622; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ TrendPulse Alpha Quantum Pro (Ultimate Edition)")
st.caption("Automated Multi-Indicator Live Database Scanner with Volume Spike & SuperTrend Logic")

# --- சைட் பார் அமைப்புகள் ---
st.sidebar.header("⚙️ Mega Scanner Controls")
market_choice = st.sidebar.selectbox("பங்குச்சந்தையைத் தேர்ந்தெடுக்கவும் (Exchange):", ["NSE (அனைத்து அசல் கம்பெனிகள்)", "BSE (அனைத்து அசல் கம்பெனிகள்)"])
scan_button = st.sidebar.button("🚀 மாசிவ் ஸ்கேனிங்கைத் தொடங்கு (Start Mega Scan)")

max_workers = 10  # 🔴 ரேட் லிமிட் தவிர்க்க workers அளவை குறைக்கיין

# --- அல்கோ-பில்டர் லாஜிக் ---
def scan_single_stock(ticker):
    try:
        data = yf.download(ticker, period="3mo", interval="1d", progress=False, group_by="ticker")
        if data.empty or len(data) < 22:
            return None
        
        close_prices = data['Close'].squeeze()
        high_prices = data['High'].squeeze()
        low_prices = data['Low'].squeeze()
        volume_data = data['Volume'].squeeze()
        
        current_close = float(close_prices.iloc[-1])
        current_volume = float(volume_data.iloc[-1])
        
        # 📊 பலம் 1: 20 SMA & 14 RSI கணக்கீடு
        sma_20 = close_prices.rolling(window=20).mean().iloc[-1]
        
        delta = close_prices.diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = (-delta.clip(upper=0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        rsi_14 = (100 - (100 / (1 + rs))).iloc[-1]
        
        # 📊 பலம் 2: அசுர வால்யூம் பில்டர்
        avg_volume_5d = volume_data.rolling(window=5).mean().iloc[-2]
        is_volume_spike = current_volume > (avg_volume_5d * 1.2)
        
        # 📊 பலம் 3: சூப்பர்-டிரெண்ட் (ATR Based Logic)
        atr_7d = (high_prices - low_prices).rolling(window=7).mean().iloc[-1]
        hl_avg = (high_prices.iloc[-1] + low_prices.iloc[-1]) / 2
        supertrend_bullish = current_close > (hl_avg - (2 * atr_7d))
        
        # பிவோட் கணக்கீடு
        last_high = float(high_prices.iloc[-2])
        last_low = float(low_prices.iloc[-2])
        last_close = float(close_prices.iloc[-2])
        
        pivot = (last_high + last_low + last_close) / 3
        day1_target = (2 * pivot) - last_low  
        day3_target = pivot + (last_high - last_low)  
        day5_target = day3_target + (last_high - last_low)  
        stoploss = pivot - (last_high - last_low)  
        
        if current_close > sma_20 and 40 < rsi_14 < 66 and is_volume_spike and supertrend_bullish:
            insight = "வலுவான வால்யூம் ஏற்றம்" if current_volume > (avg_volume_5d * 1.5) else "டிரெண்ட் பிரேக்அவுட்"
            
            return {
                "கம்பெனி": ticker.replace(".NS", "").replace(".BO", ""),
                "விலை (₹)": f"₹{current_close:.2f}",
                "RSI பலம்": f"{rsi_14:.1f}",
                "📈 நாள் 1 இலக்கு": f"₹{day1_target:.2f}",
                "🚀 நாள் 3 இலக்கு": f"₹{day3_target:.2f}",
                "🔥 நாள் 5 இலக்கு": f"₹{day5_target:.2f}",
                "🛑 ஸ்டாப்லாஸ்": f"₹{stoploss:.2f}",
                "அல்கோ-விளக்கம்": insight
            }
    except:
        return None
    return None

# --- மெயின் ஸ்கேனர் எக்ஸிகியூஷன் ---
if scan_button:
    ticker_list = []
    
    try:
        if market_choice == "NSE (அனைத்து அசல் கம்பெனிகள்)":
            nse_df = pd.read_csv("EQUITY_L.csv")
            raw_tickers = nse_df['SYMBOL'].dropna().unique()
            ticker_list = [f"{str(t).strip()}.NS" for t in raw_tickers]
            st.success("✅ `EQUITY_L.csv` மாஸ்டர் கோப்பு வெற்றிகரமாகப் படிக்கப்பட்டது.")
        else:
            # 🔴 திருத்தம்: தலைப்புகளைத் தவிர்த்து, சரியான ஸ்கிரிப் கோடு உள்ள 1-வது தூணை எடுத்தல் (Header=None அல்லது skiprows பயன்பாடு)
            bse_df = pd.read_excel("eligible.xls", skiprows=1)
            raw_tickers = bse_df.iloc[:, 1].dropna().unique() # 1-வது தூண் (Scrip Code)
            ticker_list = [f"{str(int(t)).strip()}.BO" for t in raw_tickers if str(t).strip().replace('.', '', 1).isdigit()]
            st.success("✅ `eligible.xls` மாஸ்டர் கோப்பு வெற்றிகரமாகப் படிக்கப்பட்டது.")
            
        st.info(f"🔄 மொத்தம் {len(ticker_list)} நிறுவனங்கள் கண்டறியப்பட்டுள்ளன. ஸ்கேனிங் தொடங்குகிறது...")
        
        valid_stocks = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = executor.map(scan_single_stock, ticker_list)
            for res in results:
                if res is not None:
                    valid_stocks.append(res)
                    
        st.subheader(f"🏆 இந்த வார பக்கா அல்கோ-பில்டர் முடிவுகள் (Top Breakout Stocks)")
        
        if valid_stocks:
            scanned_df = pd.DataFrame(valid_stocks)
            st.dataframe(scanned_df.head(15), use_container_width=True, hide_index=True)
            st.success(f"✅ டாப் {len(scanned_df.head(15))} முக்கிய பங்குகள் மேலே பட்டியலிடப்பட்டுள்ளன.")
        else:
            st.warning("தற்போதைய பிரேக்அவுட் எல்லையில் எந்தப் பங்கும் அமையவில்லை. லைவ் மார்க்கெட்டில் சோதிக்கவும்.")
            
    except Exception as e:
        st.error(f"கோப்புகளைப் படிப்பதில் பிழை ஏற்பட்டுள்ளது: {str(e)}")
else:
    st.info("💡 இடதுபுறம் இருக்கும் 'Start Mega Scan' பொத்தானை அழுத்தவும்.")
