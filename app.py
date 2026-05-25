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
    .stApp, .stMain {
        background-color: #0b0f19 !important;
    }
    .stMetric {
        background-color: #111827 !important;
        padding: 20px !important;
        border-radius: 12px !important;
        border: 1px solid #1f2937 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🧠 MEMORY MANAGEMENT LAYER (STATE ENGINE)
# ==========================================
if "active_trade" not in st.session_state:
    st.session_state.active_trade = {
        "status": "IDLE",       # IDLE, PENDING, CONFIRMING, ACTIVE, WON, LOST
        "ticker_label": None,
        "ticker_symbol": None,
        "direction": None,      
        "entry_poi": None,
        "sl": None,
        "tp": None,
        "rr_ratio": 0.0,
        "trade_style": None,    
        "strategy_source": None 
    }

# ==========================================
# 📡 DATA ENGINE (TRI-TIMEFRAME GENERATION)
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
        symbol = self.ticker_map.get(label, "BTC-USD")
        try:
            df_4h = yf.download(symbol, period="60d", interval="4h", progress=False)
            df_1h = yf.download(symbol, period="30d", interval="1h", progress=False)
            df_15m = yf.download(symbol, period="7d", interval="15m", progress=False)
            
            for df in [df_4h, df_1h, df_15m]:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                    
            return df_4h, df_1h, df_15m, symbol
        except Exception as e:
            st.error(f"Data engine stream timeout: {str(e)}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), symbol

# ==========================================
# 📊 MATHEMATICAL STRATEGY FRAMEWORK
# ==========================================
class TechnicalMatrix:
    @staticmethod
    def extract_fib_and_ob(df):
        if df.empty or len(df) < 50:
            return 0, 0, 0, "No Block Found"
        high_max = float(df['High'].max())
        low_min = float(df['Low'].min())
        diff = high_max - low_min
        golden_pocket = high_max - (diff * 0.618)
        tp_target = high_max - (diff * 0.236)
        ob_price = float(df['Close'].iloc[-12])
        ob_type = "Bullish OB" if float(df['Close'].iloc[-1]) > ob_price else "Bearish OB"
        return golden_pocket, tp_target, ob_price, ob_type

    @staticmethod
    def detect_fair_value_gaps(df):
        fvg_list = []
        if len(df) < 4:
            return fvg_list
        for i in range(1, len(df) - 1):
            if float(df['High'].iloc[i-1]) < float(df['Low'].iloc[i+1]) and float(df['Close'].iloc[i]) > float(df['Open'].iloc[i]):
                fvg_top = float(df['Low'].iloc[i+1])
                fvg_bottom = float(df['High'].iloc[i-1])
                fvg_list.append({"type": "BULLISH FVG", "top": fvg_top, "bottom": fvg_bottom, "mid": (fvg_top + fvg_bottom)/2})
            elif float(df['Low'].iloc[i-1]) > float(df['High'].iloc[i+1]) and float(df['Close'].iloc[i]) < float(df['Open'].iloc[i]):
                fvg_top = float(df['Low'].iloc[i-1])
                fvg_bottom = float(df['High'].iloc[i+1])
                fvg_list.append({"type": "BEARISH FVG", "top": fvg_top, "bottom": fvg_bottom, "mid": (fvg_top + fvg_bottom)/2})
        return fvg_list

    @staticmethod
    def check_market_structure(df):
        if len(df) < 20:
            return "CONSOLIDATION", 0, 0
        recent_highs = df['High'].rolling(window=10).max()
        recent_lows = df['Low'].rolling(window=10).min()
        last_close = float(df['Close'].iloc[-1])
        prev_high = float(recent_highs.iloc[-2])
        prev_low = float(recent_lows.iloc[-2])
        support = float(df['Low'].tail(30).min())
        resistance = float(df['High'].tail(30).max())
        if last_close > prev_high:
            return "BULLISH BOS", support, resistance
        elif last_close < prev_low:
            return "BEARISH BOS", support, resistance
        else:
            return "CHOPPY STRUCTURE", support, resistance

    @staticmethod
    def parse_geometric_patterns(df):
        if len(df) < 30:
            return "No Pattern Identified"
        closes = df['Close'].tail(20).values
        highs = df['High'].tail(20).values
        lows = df['Low'].tail(20).values
        high_slope = (highs[-1] - highs[0]) / 20
        low_slope = (lows[-1] - lows[0]) / 20
        if high_slope < 0 and low_slope > 0:
            return "📐 SYMMETRICAL TRIANGLE"
        elif high_slope < 0 and low_slope < 0 and abs(high_slope) > abs(low_slope):
            return "📉 FALLING WEDGE"
        elif high_slope > 0 and low_slope > 0 and low_slope > high_slope:
            return "📈 RISING WEDGE"
        elif float(df['High'].max()) == highs[0] and closes[-1] > closes[-5]:
            return "🚩 BULLISH FLAG"
        else:
            return "🔄 RANGE STRUCTURE"

# ==========================================
# 📡 BACKGROUND TRACKING & MONITORING ENGINE
# ==========================================
def run_background_monitor(engine, active_ticker_label):
    trade = st.session_state.active_trade
    
    st.sidebar.markdown("### 🛰️ System Operational Radar")
    if trade["status"] == "IDLE":
        st.sidebar.markdown("<h4 style='color:#10b981;margin:0;'>🔍 MODE: SCANNING OPEN MARKETS</h4>", unsafe_allow_html=True)
        return
    elif trade["status"] == "PENDING":
        st.sidebar.markdown("<h4 style='color:#38bdf8;margin:0;'>⏳ MODE: RADAR TRACKING POI</h4>", unsafe_allow_html=True)
    elif trade["status"] == "CONFIRMING":
        st.sidebar.markdown("<h4 style='color:#fbbf24;margin:0;'>⚠️ MODE: POI HIT - SCANNING CANDLES</h4>", unsafe_allow_html=True)
    else:
        st.sidebar.markdown("<h4 style='color:#f43f5e;margin:0;'>🔒 MODE: POSITION ACTIVE</h4>", unsafe_allow_html=True)

    _, _, df_15m, _ = engine.fetch_market_data(trade["ticker_label"])
    if df_15m.empty:
        return

    cur_close = float(df_15m['Close'].iloc[-1])
    cur_low = float(df_15m['Low'].iloc[-1])
    cur_high = float(df_15m['High'].iloc[-1])
    
    # Extract structural details of the last completed 15m candle
    c_open = float(df_15m['Open'].iloc[-2])
    c_high = float(df_15m['High'].iloc[-2])
    c_low = float(df_15m['Low'].iloc[-2])
    c_close = float(df_15m['Close'].iloc[-2])
    
    candle_range = c_high - c_low
    lower_wick = min(c_open, c_close) - c_low
    upper_wick = c_high - max(c_open, c_close)

    st.sidebar.markdown("---")
    st.sidebar.write(f"**Locked Asset:** `{trade['ticker_label']}`")
    st.sidebar.write(f"**Target POI:** `${trade['entry_poi']:.5f}`")

    # --- STATE 1: WAITING FOR PRICE TO TOUCH POI ---
    if trade["status"] == "PENDING":
        st.sidebar.info("🎯 Status: Monitoring approach toward target level...")
        st.sidebar.metric("Live Market Value", f"${cur_close:.5f}")
        
        # Invalidation Check
        if (trade["direction"] == "BUY" and cur_close < trade["sl"]) or (trade["direction"] == "SELL" and cur_close > trade["sl"]):
            st.session_state.active_trade["status"] = "IDLE"
            st.sidebar.error("❌ Setup Invalidated before hitting POI.")
            st.rerun()

        # Touch Condition Triggered
        if trade["direction"] == "BUY" and cur_low <= trade["entry_poi"]:
            st.session_state.active_trade["status"] = "CONFIRMING"
            st.rerun()
        elif trade["direction"] == "SELL" and cur_high >= trade["entry_poi"]:
            st.session_state.active_trade["status"] = "CONFIRMING"
            st.rerun()

    # --- STATE 2: POI TOUCHED - EVALUATING CANDLE CONFIRMATION ---
    elif trade["status"] == "CONFIRMING":
        st.sidebar.warning("⚡ LEVEL TOUCHED! Analyzing candle footprint validation...")
        
        if trade["direction"] == "BUY":
            # Confirmation Rule: Lower wick must be at least 40% of the entire candle structure
            if candle_range > 0 and (lower_wick / candle_range) >= 0.40 and c_close > c_open:
                st.session_state.active_trade["status"] = "ACTIVE"
                st.toast("🚨 BUY ENTRY CONFIRMED! Institutional footprints detected.", icon="🔥")
                st.rerun()
            elif cur_close < trade["sl"]:
                st.session_state.active_trade["status"] = "IDLE"
                st.sidebar.error("❌ Confirmation Failed: Price closed past invalidation block.")
                st.rerun()
        
        elif trade["direction"] == "SELL":
            # Confirmation Rule: Upper wick must be at least 40% of the entire candle structure
            if candle_range > 0 and (upper_wick / candle_range) >= 0.40 and c_close < c_open:
                st.session_state.active_trade["status"] = "ACTIVE"
                st.toast("🚨 SELL ENTRY CONFIRMED! Institutional footprints detected.", icon="🔥")
                st.rerun()
            elif cur_close > trade["sl"]:
                st.session_state.active_trade["status"] = "IDLE"
                st.sidebar.error("❌ Confirmation Failed: Price closed past invalidation block.")
                st.rerun()

    # --- STATE 3: POSITION IS RUNNING LIVE ---
    elif trade["status"] == "ACTIVE":
        st.sidebar.success("🏃 ENTRY EXECUTED: TRADING ACTIVE")
        st.sidebar.metric("Live Execution Tracker", f"${cur_close:.5f}")
        
        if trade["direction"] == "BUY":
            if cur_low <= trade["sl"]:
                st.session_state.active_trade["status"] = "LOST"
                st.rerun()
            elif cur_high >= trade["tp"]:
                st.session_state.active_trade["status"] = "WON"
                st.rerun()
        elif trade["direction"] == "SELL":
            if cur_high >= trade["sl"]:
                st.session_state.active_trade["status"] = "LOST"
                st.rerun()
            elif cur_low <= trade["tp"]:
                st.session_state.active_trade["status"] = "WON"
                st.rerun()

    elif trade["status"] in ["WON", "LOST"]:
        if trade["status"] == "WON":
            st.sidebar.balloons()
            st.sidebar.success("🎯 TARGET HIT! REWARD CAPTURED.")
        else:
            st.sidebar.error("❌ STOP TRIGGERED. POSITION CLOSED.")

    if st.sidebar.button("🗑️ Reset Matrix Radar & Unlock Scans"):
        st.session_state.active_trade = {"status": "IDLE", "ticker_label": None, "ticker_symbol": None, "direction": None, "entry_poi": None, "sl": None, "tp": None, "rr_ratio": 0.0, "trade_style": None, "strategy_source": None}
        st.rerun()

# ==========================================
# INTERFACE FRONTEND LAYOUT
# ==========================================
st.title("🎛️ Algorithmic Market Matrix Engine")
st.success("💎 **Active Version:** Upgraded Triple-POI Master Suite v3.5 (Candle-Confirmed)")
st.write(f"System Operational Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.sidebar.header("🎯 Target Selection")
market_engine = MultiTimeframeEngine()
selected_label = st.sidebar.selectbox("Select Core Trading Asset:", options=list(market_engine.ticker_map.keys()), index=0)

run_background_monitor(market_engine, selected_label)

if st.sidebar.button("⚡ Run Confluence Suite Scan"):
    with st.spinner("Analyzing multi-timeframe structural dimensions..."):
        df_4h, df_1h, df_15m, native_symbol = market_engine.fetch_market_data(selected_label)
        
        if not df_4h.empty and not df_1h.empty and not df_15m.empty:
            last_price = float(df_1h['Close'].iloc[-1])
            
            fib_gp, target_tp, block_p, block_name = TechnicalMatrix.extract_fib_and_ob(df_4h)
            fvg_records = TechnicalMatrix.detect_fair_value_gaps(df_1h)
            structure_label, static_support, static_resistance = TechnicalMatrix.check_market_structure(df_1h)
            detected_pattern = TechnicalMatrix.parse_geometric_patterns(df_1h)
            
            lt_poi = fib_gp
            fvg_mid = fvg_records[-1]["mid"] if fvg_records else (static_support + static_resistance) / 2
            dt_poi = fvg_mid if fvg_mid != 0 else last_price
            sc_poi = float(df_15m['Close'].iloc[-5])
            
            direction_bias = "BUY" if ("BULLISH" in structure_label or "Bullish" in block_name) else "SELL"
            
            st.subheader("📊 Multi-Timeframe Structural Profile")
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Live Price Valuation", f"${last_price:.5f}")
            col_m2.metric("Market Structure Bias", f"{direction_bias} Focus")
            col_m3.metric("Pattern Context", detected_pattern)
            
            fig = go.Figure(data=[go.Candlestick(
                x=df_1h.index, open=df_1h['Open'], high=df_1h['High'], low=df_1h['Low'], close=df_1h['Close'], name="1H Candles"
            )])
            
            fig.add_hline(y=lt_poi, line_dash="dash", line_color="#38bdf8", annotation_text="🌐 Long-Term Swing POI")
            fig.add_hline(y=dt_poi, line_dash="dot", line_color="#fbbf24", annotation_text="📅 Day Trade POI")
            fig.add_hline(y=sc_poi, line_dash="dashdot", line_color="#f43f5e", annotation_text="⚡ Scalp POI")
            
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            st.write("---")
            st.subheader("🎯 Automated Triple-POI Target Configurations")
            
            pois_config = [
                {"style": "LONG-TERM SWING SETUP", "entry": lt_poi, "sl_offset": 0.015, "tp_offset": 0.045},
                {"style": "DAY TRADING SETUP", "entry": dt_poi, "sl_offset": 0.005, "tp_offset": 0.018},
                {"style": "SCALPING PROFILE SETUP", "entry": sc_poi, "sl_offset": 0.002, "tp_offset": 0.006}
            ]
            
            best_rr = 0.0
            smart_recommended_style = "DAY TRADING SETUP"
            processed_cards = []
            
            for config in pois_config:
                ent = config["entry"]
                if direction_bias == "BUY":
                    sl = ent * (1.0 - config["sl_offset"])
                    tp = ent * (1.0 + config["tp_offset"])
                else:
                    sl = ent * (1.0 + config["sl_offset"])
                    tp = ent * (1.0 - config["tp_offset"])
                
                risk = abs(ent - sl)
                reward = abs(tp - ent)
                rr = reward / risk if risk > 0 else 0.0
                
                if rr > best_rr:
                    best_rr = rr
                    smart_recommended_style = config["style"]
                    
                processed_cards.append({"style": config["style"], "entry": ent, "sl": sl, "tp": tp, "rr": rr})
            
            lane1, lane2, lane3 = st.columns(3)
            lanes = [lane1, lane2, lane3]
            
            for index, card in enumerate(processed_cards):
                with lanes[index]:
                    st.markdown(f"#### `{card['style']}`")
                    st.write(f"**POI Entry Target:** `${card['entry']:.5f}`")
                    st.write(f"**Take Profit:** `${card['tp']:.5f}`")
                    st.write(f"**Stop Loss:** `${card['sl']:.5f}`")
                    st.write(f"**Risk Profile Ratio:** `1 : {card['rr']:.2f}`")
                    
                    if card['style'] == smart_recommended_style:
                        st.success("⭐ SMART ENGINE CHOICE: OPTIMAL RISK PROFILE")
            
            st.write("---")
            st.subheader("🔒 Target Optimization Arming Lock")
            
            chosen_style_label = st.selectbox("Select the specific POI target array to arm and monitor:", options=[c["style"] for c in processed_cards])
            selected_setup = next(item for item in processed_cards if item["style"] == chosen_style_label)
            
            if st.session_state.active_trade["status"] == "IDLE":
                if st.button("🔒 Arm System with Intelligent Candle Confirmation"):
                    st.session_state.active_trade = {
                        "status": "PENDING",
                        "ticker_label": selected_label,
                        "ticker_symbol": native_symbol,
                        "direction": direction_bias,
                        "entry_poi": selected_setup["entry"],
                        "sl": selected_setup["sl"],
                        "tp": selected_setup["tp"],
                        "rr_ratio": selected_setup["rr"],
                        "trade_style": selected_setup["style"],
                        "strategy_source": "Triple-POI Matrix Router"
                    }
                    st.success(f"System armed successfully! Caching parameters. Engine will monitor for touch and confirmation automatically.")
                    st.rerun()
            else:
                st.info(f"System memory currently locked onto an active target.")
