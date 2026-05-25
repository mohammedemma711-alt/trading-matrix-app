import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# ==========================================
# PAGE CONFIGURATION & THEME
# ==========================================
st.set_page_config(page_title="Algorithmic Matrix Suite Pro", layout="wide")

st.markdown("""
    <style>
    .stApp, .stMain { background-color: #0b0f19 !important; }
    .stMetric {
        background-color: #111827 !important;
        padding: 20px !important;
        border-radius: 12px !important;
        border: 1px solid #1f2937 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🧠 STATE MANAGEMENT LAYER
# ==========================================
if "active_trade" not in st.session_state:
    st.session_state.active_trade = {
        "status": "IDLE", "ticker_label": None, "ticker_symbol": None,
        "direction": None, "entry_poi": None, "sl": None, "tp": None,
        "rr_ratio": 0.0, "trade_style": None, "strategy_source": None 
    }

# ==========================================
# 📡 FINANCIAL DATA ENGINE
# ==========================================
class MultiTimeframeEngine:
    def __init__(self):
        self.ticker_map = {
            "XAUUSD (Gold)": "GC=F",
            "GBPUSD (Forex)": "GBPUSD=X",
            "EURUSD (Forex)": "EURUSD=X",
            "USDJPY (Forex)": "USDJPY=X",
            "USOIL (Crude Oil)": "CL=F",
            "BTCUSDT (Bitcoin)": "BTC-USD",
            "NAS100 (Nasdaq 100)": "^NDX"
        }

    def fetch_market_data(self, label):
        symbol = self.ticker_map.get(label, "GC=F")
        try:
            df_4h = yf.download(symbol, period="60d", interval="4h", progress=False)
            df_1h = yf.download(symbol, period="30d", interval="1h", progress=False)
            df_15m = yf.download(symbol, period="7d", interval="15m", progress=False)
            
            for df in [df_4h, df_1h, df_15m]:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
            return df_4h, df_1h, df_15m, symbol
        except Exception as e:
            st.error(f"Data stream timeout: {str(e)}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), symbol

# ==========================================
# 📊 ALIGNED TIME-FRAME CONFLUENCE ENGINE
# ==========================================
class UnifiedConfluenceEngine:
    
    @staticmethod
    def get_4h_trend_bias(df_4h):
        """Extracts macro direction based on 4-Hour EMA trend structure"""
        if df_4h.empty or len(df_4h) < 20:
            return "BUY"
        ema_fast = df_4h['Close'].ewm(span=9, adjust=False).mean().iloc[-1]
        ema_slow = df_4h['Close'].ewm(span=21, adjust=False).mean().iloc[-1]
        return "BUY" if float(ema_fast) >= float(ema_slow) else "SELL"

    @staticmethod
    def find_true_fractal_swings(df, window=5):
        """Scans for valid structural pivots on the execution frame"""
        df = df.copy()
        df['Swing_High'] = np.nan
        df['Swing_Low'] = np.nan
        
        for i in range(window, len(df) - window):
            is_high = True
            for j in range(1, window + 1):
                if df['High'].iloc[i] < df['High'].iloc[i-j] or df['High'].iloc[i] < df['High'].iloc[i+j]:
                    is_high = False
                    break
            if is_high: df.at[df.index[i], 'Swing_High'] = float(df['High'].iloc[i])
                
            is_low = True
            for j in range(1, window + 1):
                if df['Low'].iloc[i] > df['Low'].iloc[i-j] or df['Low'].iloc[i] > df['Low'].iloc[i+j]:
                    is_low = False
                    break
            if is_low: df.at[df.index[i], 'Swing_Low'] = float(df['Low'].iloc[i])
                
        high_series = df['Swing_High'].dropna()
        low_series = df['Swing_Low'].dropna()
        
        last_high = float(high_series.iloc[-1]) if not high_series.empty else float(df['High'].max())
        last_low = float(low_series.iloc[-1]) if not low_series.empty else float(df['Low'].min())
        
        return last_high, last_low, df

    @staticmethod
    def generate_synchronized_setups(df_4h, df_1h, last_price):
        """Combines all timeframes to create an optimized multi-tiered strategy profile"""
        # 1. Pull Macro Bias from 4H
        macro_bias = UnifiedConfluenceEngine.get_4h_trend_bias(df_4h)
        
        # 2. Extract Valid 1H Swing Boundaries
        sw_high, sw_low, detailed_df = UnifiedConfluenceEngine.find_true_fractal_swings(df_1h, window=5)
        range_width = sw_high - sw_low
        
        # 3. Synchronize POIs to align with the dominant Macro Bias
        if macro_bias == "BUY":
            structure_status = "BULLISH CONFLUENCE MODE"
            lt_entry = sw_low + (range_width * 0.382) # Deeper pullback (Premium entry)
            dt_entry = sw_low + (range_width * 0.500) # Equilibrium mid-range
            sc_entry = sw_low + (range_width * 0.618) # High-speed shallow momentum entry
        else:
            structure_status = "BEARISH CONFLUENCE MODE"
            lt_entry = sw_high - (range_width * 0.382)
            dt_entry = sw_high - (range_width * 0.500)
            sc_entry = sw_high - (range_width * 0.618)

        return macro_bias, structure_status, sw_high, sw_low, lt_entry, dt_entry, sc_entry, detailed_df

# ==========================================
# 📡 TRACKING MONITOR
# ==========================================
def run_background_monitor(engine):
    trade = st.session_state.active_trade
    if trade["status"] == "IDLE":
        st.sidebar.markdown("<h4 style='color:#10b981;margin:0;'>🔍 MODE: SCANNING OPEN MARKETS</h4>", unsafe_allow_html=True)
        return
    
    st.sidebar.markdown(f"<h4 style='color:#fbbf24;margin:0;'>🔒 MONITORING: {trade['trade_style']}</h4>", unsafe_allow_html=True)
    _, _, df_15m, _ = engine.fetch_market_data(trade["ticker_label"])
    if df_15m.empty: return

    cur_close = float(df_15m['Close'].iloc[-1])
    cur_low = float(df_15m['Low'].iloc[-1])
    cur_high = float(df_15m['High'].iloc[-1])
    
    # 15M Confirmation Candlestick Footprint Calculation
    c_open, c_high, c_low, c_close = df_15m['Open'].iloc[-2], df_15m['High'].iloc[-2], df_15m['Low'].iloc[-2], df_15m['Close'].iloc[-2]
    c_range = c_high - c_low
    lower_wick = min(c_open, c_close) - c_low
    upper_wick = c_high - max(c_open, c_close)

    st.sidebar.markdown("---")
    st.sidebar.write(f"**Asset:** `{trade['ticker_label']}` | **Bias Direction:** `{trade['direction']}`")
    st.sidebar.write(f"**Armed POI Target:** `${trade['entry_poi']:.2f}`")
    st.sidebar.metric("Live Market Value", f"${cur_close:.2f}")

    if trade["status"] == "PENDING":
        if (trade["direction"] == "BUY" and cur_low <= trade["entry_poi"]) or (trade["direction"] == "SELL" and cur_high >= trade["entry_poi"]):
            st.session_state.active_trade["status"] = "CONFIRMING"
            st.sidebar.warning("🎯 LEVEL HIT! Waiting for rejection wick close...")
            st.rerun()

    elif trade["status"] == "CONFIRMING":
        if trade["direction"] == "BUY" and c_range > 0 and (lower_wick / c_range) >= 0.40 and c_close > c_open:
            st.session_state.active_trade["status"] = "ACTIVE"
            st.toast("🚨 BUY ENTRY ORDER TRIGGERED!", icon="🔥")
            st.rerun()
        elif trade["direction"] == "SELL" and c_range > 0 and (upper_wick / c_range) >= 0.40 and c_close < c_open:
            st.session_state.active_trade["status"] = "ACTIVE"
            st.toast("🚨 SELL ENTRY ORDER TRIGGERED!", icon="🔥")
            st.rerun()
        elif cur_close < trade["sl"] if trade["direction"] == "BUY" else cur_close > trade["sl"]:
            st.session_state.active_trade["status"] = "IDLE"
            st.sidebar.error("❌ Level broken without confirmation.")
            st.rerun()

    elif trade["status"] == "ACTIVE":
        st.sidebar.success("🏃 SETUP RUNNING LIVE")
        if trade["direction"] == "BUY":
            if cur_low <= trade["sl"]: st.session_state.active_trade["status"] = "LOST"; st.rerun()
            elif cur_high >= trade["tp"]: st.session_state.active_trade["status"] = "WON"; st.rerun()
        else:
            if cur_high >= trade["sl"]: st.session_state.active_trade["status"] = "LOST"; st.rerun()
            elif cur_low <= trade["tp"]: st.session_state.active_trade["status"] = "WON"; st.rerun()

    if st.sidebar.button("🗑️ Reset Engine"):
        st.session_state.active_trade = {"status": "IDLE", "ticker_label": None, "ticker_symbol": None, "direction": None, "entry_poi": None, "sl": None, "tp": None, "rr_ratio": 0.0, "trade_style": None, "strategy_source": None}
        st.rerun()

# ==========================================
# WORKSPACE DISPLAY INTERFACE
# ==========================================
st.title("🎛️ Harmonized Multi-Timeframe Matrix Engine")
st.caption("Strategic Coordination Layer: Synchronizes 4H Trend Bias, 1H Fractal Swings, and 15M Entry confirmations.")

market_engine = MultiTimeframeEngine()
selected_label = st.sidebar.selectbox("Core Target Asset:", options=list(market_engine.ticker_map.keys()), index=0)

run_background_monitor(market_engine)

if st.sidebar.button("⚡ Run Harmonized Confluence Scan"):
    with st.spinner("Synchronizing structural layers..."):
        df_4h, df_1h, df_15m, native_symbol = market_engine.fetch_market_data(selected_label)
        
        if not df_1h.empty and not df_4h.empty:
            last_price = float(df_1h['Close'].iloc[-1])
            
            # Execute top-down timeframe synchronization pipeline
            bias, struct_lbl, sw_high, sw_low, lt_poi, dt_poi, sc_poi, plotted_df = \
                UnifiedConfluenceEngine.generate_synchronized_setups(df_4h, df_1h, last_price)
            
            st.subheader("🛡️ Multi-Timeframe Structural Verification")
            col_d1, col_d2, col_d3 = st.columns(3)
            col_d1.metric("Live Market Value", f"${last_price:.2f}")
            col_d2.metric("Verified Swing High Floor", f"${sw_high:.2f}")
            col_d3.metric("Verified Swing Low Ceiling", f"${sw_low:.2f}")
            
            st.info(f"📈 **Macro Condition Matrix:** {struct_lbl} | Dominant 4H Order Flow Bias: **{bias}**")
            
            # Master Plot
            fig = go.Figure(data=[go.Candlestick(
                x=plotted_df.index, open=plotted_df['Open'], high=plotted_df['High'], low=plotted_df['Low'], close=plotted_df['Close'], name="1H Candles"
            )])
            
            # Render clear structural references onto the chart canvas
            fig.add_hline(y=sw_high, line_dash="solid", line_color="#ef4444", line_width=2, annotation_text="❌ Validated Swing High Anchor")
            fig.add_hline(y=sw_low, line_dash="solid", line_color="#10b981", line_width=2, annotation_text="✅ Validated Swing Low Anchor")
            
            fig.add_hline(y=lt_poi, line_dash="dash", line_color="#38bdf8", annotation_text="🌐 UNIFIED SWING POI")
            fig.add_hline(y=dt_poi, line_dash="dot", line_color="#fbbf24", annotation_text="📅 UNIFIED DAY TRADE POI")
            fig.add_hline(y=sc_poi, line_dash="dashdot", line_color="#f43f5e", annotation_text="⚡ UNIFIED SCALP POI")
            
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # Build and display target configurations
            st.markdown("---")
            st.subheader("🎯 Synchronized Strategy Blueprint Outputs")
            
            pois_config = [
                {"style": "LONG-TERM SWING SETUP", "entry": lt_poi, "sl_offset": 0.012, "tp_offset": 0.045},
                {"style": "DAY TRADING SETUP", "entry": dt_poi, "sl_offset": 0.005, "tp_offset": 0.020},
                {"style": "SCALPING PROFILE SETUP", "entry": sc_poi, "sl_offset": 0.002, "tp_offset": 0.008}
            ]
            
            l1, l2, l3 = st.columns(3)
            lanes = [l1, l2, l3]
            processed_setups = []
            
            for index, config in enumerate(pois_config):
                ent = config["entry"]
                sl = ent * (1.0 - config["sl_offset"]) if bias == "BUY" else ent * (1.0 + config["sl_offset"])
                tp = ent * (1.0 + config["tp_offset"]) if bias == "BUY" else ent * (1.0 - config["tp_offset"])
                rr = abs(tp - ent) / abs(ent - sl)
                processed_setups.append({"style": config["style"], "entry": ent, "sl": sl, "tp": tp, "rr": rr})
                
                with lanes[index]:
                    st.markdown(f"### `{config['style']}`")
                    st.markdown(f"**Synchronized POI:** `${ent:.2f}`")
                    st.write(f"**Risk Profile Ratio:** `1 : {rr:.2f}`")
            
            st.write("---")
            st.subheader("🔒 Arm Synchronized Matrix Router")
            chosen_style = st.selectbox("Select high-confluence target array to arm:", options=[c["style"] for c in pois_config])
            selected_setup = next(item for item in processed_setups if item["style"] == chosen_style)
            
            if st.session_state.active_trade["status"] == "IDLE":
                if st.button("🔒 Arm System Strategy Suite"):
                    st.session_state.active_trade = {
                        "status": "PENDING", "ticker_label": selected_label, "ticker_symbol": native_symbol,
                        "direction": bias, "entry_poi": selected_setup["entry"], "sl": selected_setup["sl"], "tp": selected_setup["tp"],
                        "rr_ratio": selected_setup["rr"], "trade_style": selected_setup["style"], "strategy_source": "Unified Multi-Timeframe Engine"
                    }
                    st.success(f"System armed! Background matrix linked to `{selected_setup['style']}`.")
                    st.rerun()
