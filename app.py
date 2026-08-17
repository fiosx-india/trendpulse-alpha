import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

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

max_workers = 10  # சர்வர் பிளாக் (Rate Limit) ஆகாமல் இருக்க த்ரெட் கட்டுப்பாடு

# --- அல்கோ-பில்டர் லாஜிக் ---
def scan_single_stock(ticker):
    try:
        data = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if data is None or data.empty or len(data) < 22:
            return None
        
        # Multi-Index அல்லது Single Index சரிசெய்தல்
        if isinstance(data.columns, pd.MultiIndex):
            close_prices = data['Close'].iloc[:, 0]
            high_prices = data['High'].iloc[:, 0]
            low_prices = data['Low'].iloc[:, 0]
            volume_data = data['Volume'].iloc[:, 0]
        else:
            close_prices = data['Close']
            high_prices = data['High']
            low_prices = data['Low']
            volume_data = data['Volume']
            
        current_close = float(close_prices.iloc[-1])
        current_volume = float(volume_data.iloc[-1])
        
        # 📊 20 SMA & 14 RSI கணக்கீடு
        sma_20 = float(close_prices.rolling(window=20).mean().iloc[-1])
        
        delta = close_prices.diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = (-delta.clip(upper=0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        rsi_14 = float((100 - (100 / (1 + rs))).iloc[-1])
        
        # 📊 வால்யூம் பில்டர்
        avg_volume_5d = float(volume_data.rolling(window=5).mean().iloc[-2])
        is_volume_spike = current_volume > (avg_volume_5d * 1.2)
        
        # 📊 சூப்பர்-டிரெண்ட் & ATR
        atr_7d = float((high_prices - low_prices).rolling(window=7).mean().iloc[-1])
        hl_avg = float((high_prices.iloc[-1] + low_prices.iloc[-1]) / 2)
        supertrend_bullish = current_close > (hl_avg - (2 * atr_7d))
        
        # பிவோட் டார்கெட்டுகள்
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
    except Exception:
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
            # BSE கோப்பிற்கான துல்லியமான வாசிப்பு (Eligible Excel Structure)
            bse_df = pd.read_excel("eligible.xlsx", skiprows=1, engine='openpyxl')
            
            # ஸ்கிரிப் கோடு எங்குள்ளது எனச் சரிபார்த்தல்
            if 'Scrip Code' in bse_df.columns:
                raw_tickers = bse_df['Scrip Code'].dropna().unique()
            else:
                raw_tickers = bse_df.iloc[:, 1].dropna().unique()
                
            ticker_list = [f"{str(int(t)).strip()}.BO" for t in raw_tickers if str(t).strip().replace('.', '', 1).isdigit()]
            st.success("✅ `eligible.xls` மாஸ்டர் கோப்பு வெற்றிகரமாகப் படிக்கப்பட்டது.")
            
        st.info(f"🔄 மொத்தம் {len(ticker_list)} நிறுவனங்கள் கண்டறியப்பட்டுள்ளன. ஸ்கேனிங் தொடங்குகிறது...")
        
        valid_stocks = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = executor.map(scan_single_stock, ticker_list)
            for res in results:
                if res is not None:
                    valid_stocks.append(res)
                    
        st.subheader(f"🏆 பக்கா அல்கோ-பில்டர் முடிவுகள் (Top Breakout Stocks)")
        
        if valid_stocks:
            scanned_df = pd.DataFrame(valid_stocks)
            st.dataframe(scanned_df.head(15), width='stretch', hide_index=True)
            st.success(f"✅ டாப் {len(scanned_df.head(15))} முக்கிய பங்குகள் மேலே பட்டியலிடப்பட்டுள்ளன.")
        else:
            st.warning("தற்போதைய நிபந்தனைகளுக்குப் பொருந்தும் பங்குகள் எதுவும் கிடைக்கவில்லை. நேரடிச் சந்தை நேரத்தில் மீண்டும் முயற்சிக்கவும்.")
            
    except Exception as e:
        st.error(f"கோப்புகளைப் படிப்பதில் பிழை ஏற்பட்டுள்ளது: {str(e)}")
else:
    st.info("💡 இடதுபுறம் இருக்கும் 'Start Mega Scan' பொத்தானை அழுத்தவும்.")
