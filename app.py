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
st.header("🧾 அதிகாரப்பூர்வ இன்வாய்ஸ் & ஈ-வே பில் ஜெனரேட்டர்")

with st.expander(
    "👉 பிசினஸ் இன்வாய்ஸ் & ஈ-வே பில் உருவாக்குவதற்கு இங்கே கிளிக் செய்யவும்"
):

  # 1. சப்ளையர் (உங்கள்) கம்பெனி விவரங்கள் (தலைப்பு)
  st.subheader("🏢 1. சப்ளையர் (உங்கள்) விவரங்கள்")
  my_company_name = st.text_input("உங்கள் கம்பெனி பெயர்", "")
  my_gstin = st.text_input("உங்கள் GSTIN எண்", "")
  my_address = st.text_area("உங்கள் கம்பெனி முகவரி", "")

  st.markdown("---")

  # 2. Billed To மற்றும் Shipped To விவரங்கள் (இரண்டு பிரிவுகள்)
  st.subheader(
      "👥 2. வாடிக்கையாளர் மற்றும் முகவரி விவரங்கள் (Billed To & Shipped To)"
  )

  col_b1, col_b2 = st.columns(2)

  with col_b1:
    st.markdown("**Billed To (பில் பெறുന്നவர்):**")
    billed_name = st.text_input("நிறுவனத்தின் பெயர் (Billed To Name)")
    billed_gstin = st.text_input("GSTIN (Billed To GSTIN)")
    billed_address = st.text_area("முகவரி (Billed To Address)")

  with col_b2:
    st.markdown("**Shipped To (பொருள் அனுப்பப்படும் இடம்):**")
    shipped_name = st.text_input("நிறுவனத்தின் பெயர் (Shipped To Name)")
    shipped_gstin = st.text_input("GSTIN (Shipped To GSTIN)")
    shipped_address = st.text_area("முகவரி (Shipped To Address)")

  st.markdown("---")

  # 3. பொருள் மற்றும் விலை விவரங்கள்
  st.subheader("📦 3. பொருள் மற்றும் விலை விவரங்கள்")
  col_i1, col_i2, col_i3, col_i4 = st.columns(4)
  with col_i1:
    item_name = st.text_input("பொருள் விளக்கம் (Description)")
  with col_i2:
    hsn_code = st.text_input("HSN/SAC குறியீடு", "84481110")
  with col_i3:
    qty = st.number_input("எண்ணிக்கை (Qty)", min_value=1.0, value=1.0)
  with col_i4:
    price = st.number_input("விலை (Rate per unit)", min_value=0.0, value=100.0)

  gst_rate = st.selectbox("ஜிஎஸ்டி சதவீதம் (GST %)", [5.0, 12.0, 18.0, 28.0])

  st.markdown("---")

  # 4. ஈ-வே பில் விருப்பம் (தேவைப்பட்டால் மட்டும்)
  st.subheader("🚛 4. ஈ-வே பில் (E-Way Bill) விவரங்கள்")
  enable_eway = st.checkbox(
      "இந்தப் பரிவர்த்தனைக்கு ஈ-வே பில் (E-Way Bill) தேவைப்படுகிறது (டிக்"
      " செய்யவும்)"
  )

  eway_no = ""
  vehicle_no = ""
  if enable_eway:
    eway_no = st.text_input("ஈ-வே பில் எண் (E-Way Bill No)")
    vehicle_no = st.text_input("வாகன எண் / ரோடு எண் (Vehicle No)")

  st.markdown("---")

  # 5. டிஜிட்டல் கையெழுத்து & வங்கி விவரங்கள்
  st.subheader("✍️ 5. டிஜிட்டல் கையெழுத்து & வங்கி விவரங்கள்")
  bank_details = st.text_area(
      "வங்கி விவரங்கள் (Bank Details)",
      "Bank Name: \nA/c No: \nIFSC: \nBranch: ",
  )

  sig_file = st.file_uploader(
      "அதிகாரப்பூர்வ கையெழுத்து படம் (PNG/JPG) அப்லோட் செய்யவும்:",
      type=["png", "jpg", "jpeg"],
      key="exact_sig_upload",
  )

  if sig_file is not None:
    st.image(sig_file, width=150, caption="பதிவேற்றப்பட்ட கையெழுத்து")

  st.markdown("---")

  # 6. பில் உருவாக்கும் பட்டன்
  if st.button("அதிகாரப்பூர்வ இன்வாய்ஸ் மற்றும் பில்லை உருவாக்கு"):
    taxable_amount = qty * price
    tax_amount = (taxable_amount * gst_rate) / 100
    net_amount = taxable_amount + tax_amount

    st.markdown("---")

    # இன்வாய்ஸ் ஹெட்டர் (உங்கள் கம்பெனி)
    st.markdown(f"## 📌 **{my_company_name}**")
    st.write(f"{my_address}")
    st.write(f"**GSTIN:** {my_gstin}")
    st.markdown("---")

    # Billed To மற்றும் Shipped To பக்கவாட்டுத் தோற்றம்
    col_res1, col_res2 = st.columns(2)
    with col_res1:
      st.markdown(
          f"**Billed To:**\n\n{billed_name}\n\nGSTIN:"
          f" {billed_gstin}\n\n{billed_address}"
      )
    with col_res2:
      st.markdown(
          f"**Shipped To:**\n\n{shipped_name}\n\nGSTIN:"
          f" {shipped_gstin}\n\n{shipped_address}"
      )

    st.markdown("---")
    st.write(f"**பொருள்:** {item_name} (HSN: {hsn_code})")
    st.write(f"**எண்ணிக்கை:** {qty} | **விலை:** ₹{price:.2f}")
    st.write(f"**டாக்ஸபிள் தொகை (Taxable Amount):** ₹{taxable_amount:.2f}")
    st.write(f"**GST ({gst_rate}%):** ₹{tax_amount:.2f}")
    st.markdown(f"### **நிகர மொத்தம் (Net Amount): ₹{net_amount:.2f}**")

    # ஈ-வே பில் விவரம் (டிக் செய்திருந்தால் மட்டும் காட்டும்)
    if enable_eway:
      st.markdown("---")
      st.subheader("🚚 E-Way Bill Details")
      st.write(f"**E-Way Bill No:** {eway_no}")
      st.write(f"**Vehicle No:** {vehicle_no}")
      st.success("ஈ-வே பில் தகவல்கள் இன்வாய்ஸில் இணைக்கப்பட்டன.")

    st.markdown("---")
    st.markdown(f"**வங்கி விவரங்கள்:**\n{bank_details}")

    # கையெழுத்து பகுதி
    if sig_file is not None:
      st.markdown("---")
      st.write("Authorised Signatory:")
      st.image(sig_file, width=150)

    st.success("இன்வாய்ஸ் மற்றும் பில் விவரங்கள் வெற்றிகரமாகத் தயாராகிவிட்டன!")
