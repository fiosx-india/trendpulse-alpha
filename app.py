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

max_workers = 30 

# --- அல்கோ-பில்டர் லாஜிக் (3 அசுர பலங்களுடன்) ---
def scan_single_stock(ticker):
    try:
        # வரலாற்றுத் தரவுகளை அதிவேகமாக எடுத்தல்
        data = yf.download(ticker, period="3mo", interval="1d", progress=False, group_by="ticker")
        if data.empty or len(data) < 22:
            return None
        
        close_prices = data['Close'].squeeze()
        high_prices = data['High'].squeeze()
        low_prices = data['Low'].squeeze()
        volume_data = data['Volume'].squeeze()
        
        current_close = float(close_prices.iloc[-1])
        prev_close = float(close_prices.iloc[-2])
        current_volume = float(volume_data.iloc[-1])
        
        # 📊 பலம் 1: 20 SMA & 14 RSI கணக்கீடு
        sma_20 = close_prices.rolling(window=20).mean().iloc[-1]
        
        delta = close_prices.diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = (-delta.clip(upper=0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        rsi_14 = (100 - (100 / (1 + rs))).iloc[-1]
        
        # 📊 பலம் 2: அசுர வால்யூம் பில்டர் (கடந்த 5 நாட்களின் சராசரி வால்யூம் விட இன்று அதிகம் இருக்க வேண்டும்)
        avg_volume_5d = volume_data.rolling(window=5).mean().iloc[-2]
        is_volume_spike = current_volume > (avg_volume_5d * 1.2) # 20% வால்யூம் அதிகம் இருக்க வேண்டும்
        
        # 📊 பலம் 3: எளிய சூப்பர்-டிரெண்ட் (ATR Based Logic)
        # கடந்த 7 நாட்களின் ஹை-லோ வித்தியாசத்தை வைத்து எளிய டிரெண்ட் கணிப்பு
        atr_7d = (high_prices - low_prices).rolling(window=7).mean().iloc[-1]
        hl_avg = (high_prices.iloc[-1] + low_prices.iloc[-1]) / 2
        supertrend_bullish = current_close > (hl_avg - (2 * atr_7d))
        
        # பிவோட் முறைப்படி 1 முதல் 5 நாட்களுக்கான அல்கோ-டார்கெட் லெவல்கள்
        last_high = float(high_prices.iloc[-2])
        last_low = float(low_prices.iloc[-2])
        last_close = float(close_prices.iloc[-2])
        
        pivot = (last_high + last_low + last_close) / 3
        
        day1_target = (2 * pivot) - last_low  
        day3_target = pivot + (last_high - last_low)  
        day5_target = day3_target + (last_high - last_low)  
        stoploss = pivot - (last_high - last_low)  
        
        # 🎯 அல்டிமேட் பில்டர் விதி: விலை 20 SMA-க்கு மேல் இருக்க வேண்டும், RSI 40-66க்குள் இருக்க வேண்டும், 
        # வால்யூம் பலமாக இருக்க வேண்டும் மற்றும் சூப்பர் டிரெண்ட் சாதகமாக இருக்க வேண்டும்!
        if current_close > sma_20 and 40 < rsi_14 < 66 and is_volume_spike and supertrend_bullish:
            
            # தமிழ் அல்கோ-விளக்கம்
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
            bse_df = pd.read_excel("eligible.xls")
            raw_tickers = bse_df.iloc[:, 0].dropna().unique()
            ticker_list = [f"{str(t).strip()}.BO" for t in raw_tickers if str(t).strip().isdigit()]
            st.success("✅ `eligible.xls` மாஸ்டர் கோப்பு வெற்றிகரமாகப் படிக்கப்பட்டது.")
            
        st.info(f"🔄 மொத்தம் {len(ticker_list)} நிறுவனங்கள் கண்டறியப்பட்டுள்ளன. வால்யூம் & சூப்பர்-டிரெண்ட் கொண்டு அசுர வேக ஸ்கேனிங் செய்யப்படுகிறது...")
        
        valid_stocks = []
        
        # ⚡ அதிவேக பேரலல் பிராசஸிங் எஞ்சின் ஸ்டார்ட்
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = executor.map(scan_single_stock, ticker_list)
            for res in results:
                if res is not None:
                    valid_stocks.append(res)
                    
        # 📈 முடிவுகளை அட்டவணையாகக் காட்டுதல்
        st.subheader(f"🏆 இந்த வார பக்கா அல்கோ-பில்டர் முடிவுகள் (Top Breakout Stocks)")
        
        if valid_stocks:
            scanned_df = pd.DataFrame(valid_stocks)
            st.dataframe(scanned_df.head(15), use_container_width=True, hide_index=True)
            st.success(f"✅ வால்யூம் மற்றும் டிரெண்ட் வடிகட்டப்பட்டு, ஏறும் தன்மையுடைய டாப் {len(scanned_df.head(15))} முக்கிய பங்குகள் மேலே பட்டியலிடப்பட்டுள்ளன.")
        else:
            st.warning("Exchange சர்வர் தற்போது விடுமுறையில் உள்ளதாலும், நமது கூடுதல் விதிகளுக்குப் பொருந்தாததாலும் தற்போதைய பிரேக்அவுட் எல்லையில் எந்தப் பங்கும் அமையவில்லை. திங்கள் முதல் வெள்ளி வரை லைவ் மார்க்கெட்டில் சோதிக்கவும்.")
            
    except Exception as e:
        st.error(f"கோப்புகளைப் படிப்பதில் பிழை ஏற்பட்டுள்ளது: {str(e)}")
else:
    st.info("💡 இடதுபுறம் இருக்கும் 'Start Mega Scan' பொத்தானை அழுத்தினால், ஆப் தானாகவே முழு அசல் மாஸ்டர் பைல்களையும் ஸ்கேன் செய்யத் தொடங்கும்.")
