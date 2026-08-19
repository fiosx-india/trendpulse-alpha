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
            bse_df = pd.read_csv("BhavCopy_BSE_CM_0_0_0_20260818_F_0000.CSV", on_bad_lines='skip')
            
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








import urllib.parse
import streamlit as st

st.markdown("---")
st.header("🧾 முழுமையான டேக்ஸ் இன்வாய்ஸ் (Tax Invoice & WhatsApp/PDF Share)")

with st.expander("👉 இன்வாய்ஸ் விவரங்களை உள்ளிட இங்கே கிளிக் செய்யவும்"):

  # 1. சப்ளையர் (உங்கள்) கம்பெனி விவரங்கள்
  st.subheader("🏢 சப்ளையர் விவரங்கள் (Supplier Details)")
  col_s1, col_s2 = st.columns(2)
  with col_s1:
    comp_name = st.text_input("கம்பெனி பெயர் (Company Name)", "")
    comp_addr = st.text_area("கம்பெனி முகவரி (Address)", "")
    comp_phone = st.text_input("தொலைபேசி எண் (Phone)", "")
  with col_s2:
    comp_gstin = st.text_input("GSTIN", "")
    comp_pan = st.text_input("PAN", "")

  st.markdown("---")

  # 2. பில் மற்றும் ரசீது எண் விவரங்கள்
  st.subheader("📋 பில் மற்றும் ஒப்புதல் விவரங்கள் (Bill & Ack Details)")
  col_a1, col_a2 = st.columns(2)
  with col_a1:
    bill_no = st.text_input("பில் எண் (BILL NO)", "")
    bill_date = st.text_input("பில் தேதி (BILL DATE)", "")
    ack_no = st.text_input("Ack No", "")
    ack_date = st.text_input("Ack Date", "")
  with col_a2:
    irn_no = st.text_input("I.R.N", "")
    eway_no = st.text_input("EWAY BILL NO", "")
    invoice_type = st.text_input(
        "இன்வாய்ஸ் வகை", "ORIGINAL FOR CONSIGNEE"
    )

  st.markdown("---")

  # 3. Billed To மற்றும் Shipped To விவரங்கள்
  st.subheader("👥 பெறுபவர் மற்றும் அனுப்புமிடம் (Billed To & Shipped To)")
  col_b1, col_b2 = st.columns(2)

  with col_b1:
    st.markdown("**Billed To:**")
    billed_name = st.text_input("பெறுபவர் கம்பெனி பெயர்", "")
    billed_addr = st.text_area("பெறுபவர் முகவரி", "")
    billed_gstin = st.text_input("பெறுபவர் GSTIN", "")
    billed_pan = st.text_input("பெறுபவர் PAN", "")

  with col_b2:
    st.markdown("**Shipped To:**")
    shipped_name = st.text_input("அனுப்பும் இடம் கம்பெனி பெயர்", "")
    shipped_addr = st.text_area("அனுப்பும் இடம் முகவரி", "")
    shipped_gstin = st.text_input("அனுப்பும் இடம் GSTIN", "")

  st.markdown("---")

  # 4. பொருட்கள் விவரங்கள்
  st.subheader("📦 பொருள் விவரங்கள் (Goods Details)")
  desc = st.text_input("பொருள் விளக்கம் (Description of Goods)", "")
  col_g1, col_g2, col_g3, col_g4, col_g5 = st.columns(5)
  with col_g1:
    hsn_sac = st.text_input("HSN/SAC", "")
  with col_g2:
    tax_rate = st.number_input("Tax %", value=18.0)
  with col_g3:
    qty = st.number_input("Qty", value=1.0)
  with col_g4:
    uom = st.text_input("UOM", "NOS")
  with col_g5:
    rate = st.number_input("Rate (தொகை)", value=0.0)

  # தானியங்கு வரி கணக்கீடு (Auto calculation based on Rate & Qty)
  taxable_amt = qty * rate
  total_tax_amount = (taxable_amt * tax_rate) / 100

  # மாநில உள்ளூர் விற்பனை எனில் CGST & SGST சமமாகப் பிரியும் (பாதி பாதியாக), இல்லையெனில் IGST முழுமையாக வரும்
  tax_type = st.radio(
      "வரி வகை (Tax Type)", ["Local (CGST + SGST)", "Inter-State (IGST)"]
  )

  if tax_type == "Local (CGST + SGST)":
    cgst_amt = total_tax_amount / 2
    sgst_amt = total_tax_amount / 2
    igst_amt = 0.0
  else:
    cgst_amt = 0.0
    sgst_amt = 0.0
    igst_amt = total_tax_amount

  st.markdown("---")
  st.subheader("💰 வரித் தொகைகள் (Tax Breakdown - Auto Calculated)")
  col_t1, col_t2, col_t3 = st.columns(3)
  with col_t1:
    st.metric(label="CGST Amount", value=f"₹ {cgst_amt:,.2f}")
  with col_t2:
    st.metric(label="SGST Amount", value=f"₹ {sgst_amt:,.2f}")
  with col_t3:
    st.metric(label="IGST Amount", value=f"₹ {igst_amt:,.2f}")

  st.markdown("---")

  # 5. வங்கி மற்றும் வாகன விவரங்கள்
  st.subheader("🏦 வங்கி, வாகன எண் & வாடிக்கையாளர் வாட்ஸ்அப்")
  col_v1, col_v2 = st.columns(2)
  with col_v1:
    vehicle_no = st.text_input("வாகன எண் (VEHICLE NO)", "")
    bank_name = st.text_input("வங்கி பெயர் (BANK NAME)", "")
    account_no = st.text_input("கணக்கு எண் (ACCOUNT NO)", "")
    customer_phone = st.text_input(
        "வாடிக்கையாளர் வாட்ஸ்அப் எண் (எ.கா: 919876543210)", ""
    )
  with col_v2:
    branch = st.text_input("கிளை (BRANCH)", "")
    ifsc = st.text_input("IFSC", "")
    terms_cond = st.text_area(
        "விதிமுறைகள் (Terms & Conditions)",
        "Overdue interest will be charged at 24% from the invoice date.",
    )

  sig_file = st.file_uploader(
      "கையொப்ப படம் (Sign)", type=["png", "jpg", "jpeg"]
  )

  st.markdown("---")

  # 6. இன்வாய்ஸ் உருவாக்கும் பட்டன்
  if st.button("அதிகாரப்பூர்வ இன்வாய்ஸை உருவாக்கு"):
    net_amt = taxable_amt + total_tax_amount

    invoice_html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; border: 1px solid #ddd; background-color: #fff; color: #000;">
            <div style="text-align: right; font-weight: bold; font-size: 12px;">{invoice_type}</div>
            <h2 style="text-align: center; margin-bottom: 5px;">{comp_name}</h2>
            <p style="text-align: center; margin: 0; font-size: 14px;">{comp_addr}</p>
            <p style="text-align: center; margin: 5px 0; font-size: 14px;">PHONE : {comp_phone}</p>
            <hr>
            <p><b>GSTIN :</b> {comp_gstin} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>PAN :</b> {comp_pan}</p>
            <hr>
            <table width="100%">
                <tr>
                    <td><b>BILL NO :</b> {bill_no}<br><b>BILL DATE :</b> {bill_date}</td>
                    <td style="text-align: right;"><b>Ack No :</b> {ack_no}<br><b>Ack Date :</b> {ack_date}</td>
                </tr>
            </table>
            <p><b>I.R.N :</b> {irn_no}</p>
            <p><b>EWAY BILL NO :</b> {eway_no}</p>
            <hr>
            <table width="100%">
                <tr>
                    <td width="50%" style="vertical-align: top;">
                        <b>Billed To:</b><br>
                        <b>{billed_name}</b><br>{billed_addr}<br>
                        <b>GSTIN :</b> {billed_gstin}<br><b>PAN :</b> {billed_pan}
                    </td>
                    <td width="50%" style="vertical-align: top;">
                        <b>Shipped To:</b><br>
                        <b>{shipped_name}</b><br>{shipped_addr}<br>
                        <b>GSTIN :</b> {shipped_gstin}
                    </td>
                </tr>
            </table>
            <hr>
            <table border="1" cellspacing="0" cellpadding="5" width="100%" style="border-collapse: collapse; font-size: 12px;">
                <tr style="background-color: #f2f2f2;">
                    <th>S.NO</th><th>DESCRIPTION OF GOODS</th><th>HSN/SAC</th><th>TAX %</th><th>QTY</th><th>UOM</th><th>RATE</th><th>AMOUNT</th>
                </tr>
                <tr>
                    <td align="center">1</td>
                    <td>{desc}</td>
                    <td align="center">{hsn_sac}</td>
                    <td align="center">{tax_rate:.2f}</td>
                    <td align="center">{qty}</td>
                    <td align="center">{uom}</td>
                    <td align="right">{rate:,.2f}</td>
                    <td align="right">{taxable_amt:,.2f}</td>
                </tr>
            </table>
            <p style="text-align: right;"><b>Taxable Amount:</b> ₹ {taxable_amt:,.2f}</p>
            <p style="text-align: right;"><b>CGST Amount:</b> ₹ {cgst_amt:,.2f}</p>
            <p style="text-align: right;"><b>SGST Amount:</b> ₹ {sgst_amt:,.2f}</p>
            <p style="text-align: right;"><b>IGST Amount:</b> ₹ {igst_amt:,.2f}</p>
            <p style="text-align: right;"><b>Tax Total:</b> ₹ {total_tax_amount:,.2f}</p>
            <h3 style="text-align: right;">Net Amount: ₹ {net_amt:,.2f}</h3>
            <hr>
            <table width="100%">
                <tr>
                    <td width="60%" style="vertical-align: top; font-size: 11px;">
                        <b>Terms & Conditions:</b><br>{terms_cond}
                    </td>
                    <td width="40%" style="vertical-align: top; font-size: 11px;">
                        <b>BANK DETAIL:</b><br>
                        - ACCOUNT NO : {account_no}<br>
                        - BANK NAME : {bank_name}<br>
                        - BRANCH : {branch}<br>
                        - IFSC : {ifsc}
                    </td>
                </tr>
            </table>
            <p><b>VEHICLE NO :</b> {vehicle_no}</p>
            <div style="text-align: right; margin-top: 30px; font-weight: bold;">For {comp_name}</div>
        </div>
        """

    st.markdown(invoice_html, unsafe_allow_html=True)

    if sig_file is not None:
      st.image(sig_file, width=150)

    st.success("இன்வாய்ஸ் வெற்றிகரமாகத் தயாராகிவிட்டது!")

    st.info(
        "📥 **PDF ஆக மாற்ற / பிரிண்ட் செய்ய:** உங்கள் மொபைல் பிரவுசரில் மேலே உள்ள"
        " மூன்று புள்ளிகளை (Menu) தட்டி **'Print'** கொடுத்து **'Save as PDF'**"
        " என்பதைத் தேர்ந்தெடுக்கவும்."
    )

    whatsapp_message = (
        f"*INVOICE DETAILS*\nCompany: {comp_name}\nBill No: {bill_no}\nDate:"
        f" {bill_date}\nNet Amount: ₹ {net_amt:,.2f}\nE-Way Bill No:"
        f" {eway_no}\nThank you!"
    )
    encoded_message = urllib.parse.quote(whatsapp_message)
    whatsapp_url = f"https://wa.me/{customer_phone}?text={encoded_message}"

    if customer_phone:
      st.markdown(
          f"### 📲 [வாட்ஸ்அப்பில் பில் விவரங்களை அனுப்ப இங்கே கிளிக்"
          f" செய்யவும்]({whatsapp_url})",
          unsafe_allow_html=True,
      )
    else:
      st.warning(
          "வாட்ஸ்அப்பில் அனுப்ப மேலே உள்ள கட்டத்தில் வாடிக்கையாளர் போன் நம்பரை"
          " உள்ளிடவும்."
      )
