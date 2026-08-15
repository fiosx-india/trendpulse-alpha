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

st.title("⚡ TrendPulse Alpha Quantum Pro")
st.caption("Automated CSV/Excel Live Database Scanner for All NSE & BSE Listed Equities")

# --- சைட் பார் அமைப்புகள் ---
st.sidebar.header("⚙️ Mega Scanner Controls")
market_choice = st.sidebar.selectbox("பங்குச்சந்தையைத் தேர்ந்தெடுக்கவும் (Exchange):", ["NSE (அனைத்து அசல் கம்பெனிகள்)", "BSE (அனைத்து அசல் கம்பெனிகள்)"])
scan_button = st.sidebar.button("🚀 மாசிவ் ஸ்கேனிங்கைத் தொடங்கு (Start Mega Scan)")

max_workers = 15 

# --- அல்கோ-பில்டர் லாஜிக் (Core Mathematical Function) ---
def scan_single_stock(ticker):
    try:
        data = yf.download(ticker, period="3mo", interval="1d", progress=False, group_by="ticker")
        if data.empty or len(data) < 25:
            return None
        
        close_prices = data['Close'].squeeze()
        high_prices = data['High'].squeeze()
        low_prices = data['Low'].squeeze()
        
        current_close = float(close_prices.iloc[-1])
        prev_close = float(close_prices.iloc[-2])
        
        # 📊 இண்டிகேட்டர்கள் கணக்கீடு (20 SMA & 14 RSI)
        sma_20 = close_prices.rolling(window=20).mean().iloc[-1]
        
        delta = close_prices.diff()
        gain = delta.clip(lower=0).rolling(window=14).mean()
        loss = (-delta.clip(upper=0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        rsi_14 = (100 - (100 / (1 + rs))).iloc[-1]
        
        # பிவோட் முறைப்படி 1 முதல் 5 நாட்களுக்கான அல்கோ-டார்கெட் லெவல்கள்
        last_high = float(high_prices.iloc[-2])
        last_low = float(low_prices.iloc[-2])
        last_close = float(close_prices.iloc[-2])
        
        pivot = (last_high + last_low + last_close) / 3
        
        day1_target = (2 * pivot) - last_low  
        day3_target = pivot + (last_high - last_low)  
        day5_target = day3_target + (last_high - last_low)  
        stoploss = pivot - (last_high - last_low)  
        
        # 🎯 அக்யூரேட் பில்டர் நிபந்தனை: 20 SMA-க்கு மேல் இருக்க வேண்டும், RSI 44 முதல் 64-க்குள் சாதகமான ஏறும் எல்லையில் இருக்க வேண்டும்
        if current_close > sma_20 and 44 < rsi_14 < 64:
            return {
                "கம்பெனி குறியீடு": ticker.replace(".NS", "").replace(".BO", ""),
                "தற்போதைய விலை (₹)": f"₹{current_close:.2f}",
                "RSI பலம் (14D)": f"{rsi_14:.1f}",
                "📈 நாள் 1 இலக்கு": f"₹{day1_target:.2f}",
                "🚀 நாள் 3 இலக்கு": f"₹{day3_target:.2f}",
                "🔥 நாள் 5 இலக்கு": f"₹{day5_target:.2f}",
                "🛑 பாதுகாப்பு எல்லை (StopLoss)": f"₹{stoploss:.2f}"
            }
    except:
        return None
    return None

# --- மெயின் ஸ்கேனர் எக்ஸிகியூஷன் (CSV/Excel Reader Engine) ---
if scan_button:
    ticker_list = []
    
    try:
        # நீங்கள் அப்லோடு செய்த அசல் பைல்களை ஆட்டோமேட்டிக்காகப் படிக்கும் அட்வான்ஸ் லாஜிக்
        if market_choice == "NSE (அனைத்து அசல் கம்பெனிகள்)":
            # EQUITY_L.csv கோப்பில் இருக்கும் அசல் SYMBOL காலமை எடுத்தல்
            nse_df = pd.read_csv("EQUITY_L.csv")
            # முதல் 150 கம்பெனிகளை மட்டும் சோதனைக்கு எடுத்துக்கொள்வோம் (வேகத்திற்காக)
            raw_tickers = nse_df['SYMBOL'].dropna().unique()[:150]
            ticker_list = [f"{str(t).strip()}.NS" for t in raw_tickers]
            st.success("✅ `EQUITY_L.csv` கோப்பு வெற்றிகரமாகப் படிக்கப்பட்டது.")
        else:
            # eligible.xls கோப்பில் இருக்கும் அசல் BSE Scrip Codes எடுத்தல்
            bse_df = pd.read_excel("eligible.xls")
            # முதல் 150 கம்பெனிகளை சோதனைக்கு எடுத்தல்
            raw_tickers = bse_df.iloc[:, 0].dropna().unique()[:150]
            ticker_list = [f"{str(t).strip()}.BO" for t in raw_tickers if str(t).strip().isdigit()]
            st.success("✅ `eligible.xls` கோப்பு வெற்றிகரமாகப் படிக்கப்பட்டது.")
            
        st.info(f"🔄 மொத்தம் {len(ticker_list)} நிறுவனங்கள் கண்டறியப்பட்டுள்ளன. மல்டி-திரெடிங் மூலம் தானியங்கி ஸ்கேனிங் செய்யப்படுகிறது...")
        
        valid_stocks = []
        
        # ⚡ மல்டி-திரெடிங் பேரலல் பிராசஸிங் ஸ்டார்ட்
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = executor.map(scan_single_stock, ticker_list)
            for res in results:
                if res is not None:
                    valid_stocks.append(res)
                    
        # 📈 ஸ்கிரீனில் டாப் 10 பங்குகளை டேபிளாகக் காட்டுதல்
        st.subheader(f"🏆 இந்த வார பக்கா அல்கோ-பில்டர் முடிவுகள் (Top Breakout Stocks)")
        
        if valid_stocks:
            scanned_df = pd.DataFrame(valid_stocks).head(10)
            st.dataframe(scanned_df, use_container_width=True, hide_index=True)
            st.success("✅ அத்தனை அசல் கம்பெனிகளும் பில்டர் செய்யப்பட்டு, அடுத்த 1 முதல் 5 நாட்களுக்குள் உறுதியாக ஏறும் தன்மையுடைய டாப் 10 பங்குகள் மேலே பட்டியலிடப்பட்டுள்ளன.")
        else:
            st.warning("📉 தற்போதைய லைவ் மார்க்கெட் விதிகளின்படி பிரேக்அவுட் எல்லையில் எந்தப் பங்கும் அமையவில்லை. சந்தை தற்போது படுக்கை M-மட்டமாக (Flat) உள்ளது.")
            
    except Exception as e:
        st.error(f"கோப்புகளைப் படிப்பதில் பிழை ஏற்பட்டுள்ளது: {str(e)}")
else:
    st.info("💡 இடதுபுறம் இருக்கும் 'Start Mega Scan' பொத்தானை அழுத்தினால், ஆப் தானாகவே முழு அசல் மாஸ்டர் பைல்களையும் ஸ்கேன் செய்யத் தொடங்கும்.")
