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

            # BSE கோப்பிற்கான வாசிப்பு மற்றும் எர்ரர் தவிர்ப்பு
            bse_df = pd.read_csv("BhavCopy_BSE_CM_0_0_0_20260817_F_0000.CSV", on_bad_lines='skip')
            
            # 1. மியூச்சுவல் ஃபண்ட், பாண்டுகளை நீக்கிவிட்டு பங்குகளை (Stocks) மட்டும் எடுக்க:
            if 'FinInstrmTp' in bse_df.columns:
                bse_df = bse_df[bse_df['FinInstrmTp'] == 'STK']

            # 2. ஸ்கிரிப் கோடு எங்குள்ளது எனச் சரிபார்த்தல் (புதிய மற்றும் பழைய பார்மட்டுகளுக்கு)
            if 'FinInstrmId' in bse_df.columns:
                raw_tickers = bse_df['FinInstrmId'].dropna().unique()
            elif 'Scrip Code' in bse_df.columns:
                raw_tickers = bse_df['Scrip Code'].dropna().unique()
            else:
                raw_tickers = bse_df.iloc[:, 5].dropna().unique()

            ticker_list = [f"{str(int(float(t))).strip()}.BO" for t in raw_tickers if str(t).strip() and str(t).replace('.','',1).isdigit()]
            st.success("`BhavCopy` மாஸ்டர் கோப்பு வெற்றிகரமாகப் படிக்கப்பட்டது.")
            
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




import streamlit as st

st.markdown("---")
st.header("🧾 அவசர ஜிஎஸ்டி & ஈ-வே பில் இன்வாய்ஸ் ஜெனரேட்டர்")

with st.expander(
    "👉 பிசினஸ் இன்வாய்ஸ் & ஈ-வே பில் உருவாக்குவதற்கு இங்கே கிளிக் செய்யவும்"
):

  # 1. உங்கள் கம்பெனி விவரங்கள் (தலைப்பு)
  st.subheader("🏢 சப்ளையர் (உங்கள்) விவரங்கள்")
  my_company_name = st.text_input(
      "உங்கள் கம்பெனி பெயர்", "TrendPulse Enterprises"
  )
  my_gstin = st.text_input("உங்கள் GSTIN எண்", "33AAAAA0000A1Z5")

  st.markdown("---")

  # 2. வாடிக்கையாளர் மற்றும் விற்பனை செய்யும் கம்பெனி விவரங்கள்
  st.subheader("👥 வாடிக்கையாளர் மற்றும் நிறுவன விவரங்கள்")
  buyer_name = st.text_input("பொருள் வாங்குபவர் பெயர் (Buyer Name)")
  buyer_gstin = st.text_input("வாங்குபவர் GSTIN எண்")

  add_second_company = st.checkbox(
      "மற்றொரு கம்பெனி பெயருக்கு விற்பனை (Secondary Company Sale இருந்தால்"
      " டிக் செய்யவும்)"
  )
  second_company_name = ""
  second_company_gstin = ""

  if add_second_company:
    second_company_name = st.text_input("இரண்டாவது கம்பெனி பெயர்")
    second_company_gstin = st.text_input("இரண்டாவது கம்பெனி GSTIN")

  st.markdown("---")

  # 3. பொருள் மற்றும் விலை விவரங்கள்
  st.subheader("📦 பொருள் மற்றும் விலை விவரங்கள்")
  col1, col2, col3 = st.columns(3)
  with col1:
    item_name = st.text_input("பொருள் பெயர் (Item Name)")
  with col2:
    qty = st.number_input("எண்ணிக்கை (Qty)", min_value=1, value=1)
  with col3:
    price = st.number_input("விலை (Price per unit)", min_value=0.0, value=100.0)

  gst_rate = st.selectbox("ஜிஎஸ்டி சதவீதம் (GST %)", [5, 12, 18, 28])

  st.markdown("---")

  # 4. ஈ-வே பில் மற்றும் வாகன எண் விருப்பம்
  st.subheader("🚛 ஈ-வே பில் (E-Way Bill) விவரங்கள்")
  enable_eway = st.checkbox(
      "இந்தப் பரிவர்த்தனைக்கு ஈ-வே பில் (E-Way Bill) தேவைப்படுகிறது"
  )
  vehicle_no = ""
  if enable_eway:
    vehicle_no = st.text_input("வாகன எண் / ரோடு எண் (Vehicle / Transport No)")

  st.markdown("---")

  # 5. டிஜிட்டல் கையெழுத்து அமைப்பு
  st.subheader("✍️ டிஜிட்டல் கையெழுத்து")
  sig_file = st.file_uploader(
      "கையெழுத்து படத்தை (PNG/JPG) அப்லோட் செய்யவும்:",
      type=["png", "jpg", "jpeg"],
      key="gst_sig",
  )

  if sig_file is not None:
    st.image(sig_file, width=150, caption="பதிவேற்றப்பட்ட கையெழுத்து")

  # 6. பில் உருவாக்கும் பட்டன்
  if st.button("இன்வாய்ஸ் மற்றும் பில்லை உருவாக்கு"):
    subtotal = qty * price
    gst_amount = (subtotal * gst_rate) / 100
    total_amount = subtotal + gst_amount

    st.markdown("---")
    # பில் பிரிண்ட் பார்மட்
    st.markdown(f"## 📌 **{my_company_name}**")
    st.write(f"**GSTIN:** {my_gstin}")
    st.markdown("---")

    st.write(f"**வாங்குபவர்:** {buyer_name} (GSTIN: {buyer_gstin})")
    if add_second_company and second_company_name:
      st.write(
          f"**இறுதி விற்பனை நிறுவனங்கள்:** {second_company_name} (GSTIN:"
          f" {second_company_gstin})"
      )

    st.write(f"**பொருள்:** {item_name} | **எண்ணிக்கை:** {qty}")
    st.write(f"**அடிப்படைத் தொகை (Subtotal):** ₹{subtotal:.2f}")
    st.write(f"**GST ({gst_rate}%):** ₹{gst_amount:.2f}")
    st.markdown(f"### **மொத்தத் தொகை (Grand Total): ₹{total_amount:.2f}**")

    # ஈ-வே பில் விவரம் (டிக் செய்திருந்தால் மட்டும் காட்டும்)
    if enable_eway:
      st.markdown("---")
      st.subheader("🚚 E-Way Bill விவரம்")
      st.success("ஈ-வே பில் கோரிக்கை ஏற்கFபட்டது.")
      st.write(f"**வாகன எண் / ரோடு எண்:** {vehicle_no}")
      st.info(
          "மேற்கண்ட விவரங்களைக் கொண்டு அதிகாரப்பூர்வ E-Way Bill போர்ட்டலில்"
          " பதிவேற்றிக் கொள்ளவும்."
      )

    # கையெழுத்து காட்டுவது
    if sig_file is not None:
      st.markdown("---")
      st.write("Authorized Signature:")
      st.image(sig_file, width=150)

    st.success("இன்வாய்ஸ் வெற்றிகரமாகத் தயாராகிவிட்டது!")

