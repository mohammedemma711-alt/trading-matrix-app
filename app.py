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
    /* Force deep dark theme across the entire application workspace */
    .stApp, .stMain {
        background-color: #0b0f19 !important;
    }
    /* Style the core technical metric display cards */
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
        "status": "IDLE",       # IDLE, PENDING, ACTIVE, WON, LOST
        "ticker_label": None,
        "ticker_symbol": None,
        "direction": None,      # BUY or SELL
        "entry_poi": None,
        "sl": None,
        "tp": None,
        "rr_ratio": 0.0,
        "trade_style": None,    # SCALPING, DAY TRADING, SWING TRADING
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
        """Calculates Order Blocks and Fibonacci Retracements"""
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
        """Identifies Unmitigated Fair Value Gaps (FVG)"""
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
        """Detects Market Structure Breaks (BOS) and Support/Resistance"""
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
            return "BULLISH BOS (Break of Structure)", support, resistance
        elif last_close < prev_low:
            return "BEARISH BOS (Break of Structure)", support, resistance
        else:
            return "CHOPPY MARKET STRUCTURE", support, resistance

    @staticmethod
    def parse_geometric_patterns(df):
        """Scans trendlines for Wedges, Flags, and Triangles"""
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
    
    # --- VISUAL RADAR STATE INDICATOR SYSTEM ---
    st.sidebar.markdown("### 🛰️ System Operational Radar")
    if trade["status"] == "IDLE":
        st.sidebar.markdown("<h4 style='color:#10b981;margin:0;'>🔍 MODE: SCANNING OPEN MARKETS</h4>", unsafe_allow_html=True)
        st.sidebar.caption("System is free and actively searching for fresh structural anomalies.")
        return
    else:
        st.sidebar.markdown("<h4 style='color:#f59e0b;margin:0;'>🔒 MODE: ARMED & TRACKING LOCK</h4>", unsafe_allow_html=True)
        st.sidebar.info(f"System memory frozen onto active setup. Ignoring other scans until exit matrix triggers.")

    _, _, df_15m, _ = engine.fetch_market_data(trade["ticker_label"])
    if df_15m.empty:
        return

    cur_close = float(df_15m['Close'].iloc[-1])
    cur_low = float(df_15m['Low'].iloc[-1])
    cur_high = float(df_15m['High'].iloc[-1])

    st.sidebar.markdown("---")
    st.sidebar.subheader("📡 Background Position Tracker")
    st.sidebar.write(f"**Locked Asset:** `{trade['ticker_label']}`")
    st.sidebar.write(f"**Classification:** `{trade['trade_style']}` ({trade['direction']})")
    st.sidebar.write(f"**Target R:R Profile:** `1 : {trade['rr_ratio']:.2f}`")

    if trade["status"] == "PENDING":
        st.sidebar.warning(f"⏳ Status: WAITING FOR POI ENTRY (${trade['entry_poi']:.5f})")
        st.sidebar.metric("Live Price Distance", f"${cur_close:.5f}")
        
        if trade["direction"] == "BUY" and cur_close < trade["sl"]:
            st.session_state.active_trade["status"] = "IDLE"
            st.sidebar.error("❌ Setup Invalidated: Price broke below Stop Loss footprint.")
            st.rerun()
        elif trade["direction"] == "SELL" and cur_close > trade["sl"]:
            st.session_state.active_trade["status"] = "IDLE"
            st.sidebar.error("❌ Setup Invalidated: Price broke above Stop Loss footprint.")
            st.rerun()

        if trade["direction"] == "BUY" and cur_low <= trade["entry_poi"]:
            st.session_state.active_trade["status"] = "ACTIVE"
            st.toast("🚨 Buy Limit Triggered! Position is Live.", icon="🔥")
            st.rerun()
        elif trade["direction"] == "SELL" and cur_high >= trade["entry_poi"]:
            st.session_state.active_trade["status"] = "ACTIVE"
            st.toast("🚨 Sell Limit Triggered! Position is Live.", icon="🔥")
            st.rerun()

    elif trade["status"] == "ACTIVE":
        st.sidebar.success("🏃 Status: POSITION LIVE & EXECUTING")
        st.sidebar.metric("Live Real-Time Price", f"${cur_close:.5f}")
        
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
            st.sidebar.success("🎯 TAKE PROFIT HIT! REWARD CAPTURED successfully.")
        else:
            st.sidebar.error("❌ STOP LOSS TRIGGERED. POSITION CLOSED.")

    if st.sidebar.button("🗑️ Force Release Lock & Resume Free Scan"):
        st.session_state.active_trade = {"status": "IDLE", "ticker_label": None, "ticker_symbol": None, "direction": None, "entry_poi": None, "sl": None, "tp": None, "rr_ratio": 0.0, "trade_style": None, "strategy_source": None}
        st.rerun()

# ==========================================
# INTERFACE FRONTEND LAYOUT
# ==========================================
st.title("🎛️ Algorithmic Market Matrix Engine")
st.success("💎 **Active Version:** Upgraded master strategy suite v2.5")
st.write(f"System Operational Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.sidebar.header("🎯 Target Selection")
market_engine = MultiTimeframeEngine()
selected_label = st.sidebar.selectbox("Select Core Trading Asset:", options=list(market_engine.ticker_map.keys()), index=0)

# Run Background Tracker Execution
run_background_monitor(market_engine, selected_label)

if st.sidebar.button("⚡ Run Confluence Suite Scan"):
    with st.spinner("Analyzing cross-timeframe structural matrices..."):
        df_4h, df_1h, df_15m, native_symbol = market_engine.fetch_market_data(selected_label)
        
        if not df_4h.empty and not df_1h.empty:
            last_price = float(df_1h['Close'].iloc[-1])
            
            fib_gp, target_tp, block_p, block_name = TechnicalMatrix.extract_fib_and_ob(df_4h)
            fvg_records = TechnicalMatrix.detect_fair_value_gaps(df_1h)
            structure_label, static_support, static_resistance = TechnicalMatrix.check_market_structure(df_1h)
            detected_pattern = TechnicalMatrix.parse_geometric_patterns(df_1h)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Live Execution Valuation", f"${last_price:.5f}")
            col2.metric("4H Confluence POI", f"${fib_gp:.5f}")
            col3.metric("Pattern Context", detected_pattern)
            
            st.info(f"🛡️ **Structure Analysis:** {structure_label} | **Horizontal Keys:** Support: `${static_support:.5f}` | Resistance: `${static_resistance:.5f}`")
            
            fig = go.Figure(data=[go.Candlestick(
                x=df_1h.index, open=df_1h['Open'], high=df_1h['High'], low=df_1h['Low'], close=df_1h['Close'], name="1H Market Feed"
            )])
            
            fig.add_hline(y=fib_gp, line_dash="dash", line_color="#e11d48", annotation_text="Fib Golden Pocket POI")
            fig.add_hline(y=static_support, line_dash="solid", line_color="#10b981", annotation_text="Major Support Floor")
            fig.add_hline(y=static_resistance, line_dash="solid", line_color="#ef4444", annotation_text="Major Resistance Ceiling")
            
            active_fvg_entry = None
            if fvg_records:
                st.subheader("⚠️ Detected Fair Value Gaps (1H Frame)")
                for fvg in fvg_records[-2:]:
                    st.warning(f"**{fvg['type']}** found between ${fvg['bottom']:.5f} and ${fvg['top']:.5f}")
                    fig.add_hrect(y0=fvg['bottom'], y1=fvg['top'], fillcolor="rgba(234, 179, 8, 0.12)", line_width=0)
                    if active_fvg_entry is None:
                        active_fvg_entry = fvg['mid']
            
            fig.update_layout(title=f"{selected_label} Live Technical Matrix Layout", template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            st.write("---")
            st.subheader("🔒 Position Protection & Engine Lock System")
            
            # --- 🛠️ ADVANCED R:R & CLASSIFICATION ENGINE ---
            if "BULLISH" in structure_label or "Bullish" in block_name:
                pred_direction = "BUY"
                pred_entry = fib_gp if active_fvg_entry is None else active_fvg_entry
                # Stop Loss safely hidden below the support floor
                pred_sl = static_support if static_support < pred_entry else pred_entry * 0.996
                # Take Profit target set at the next key structural resistance ceiling
                pred_tp = static_resistance if static_resistance > pred_entry else target_tp
            else:
                pred_direction = "SELL"
                pred_entry = fib_gp if active_fvg_entry is None else active_fvg_entry
                # Stop Loss hidden above resistance ceiling
                pred_sl = static_resistance if static_resistance > pred_entry else pred_entry * 1.004
                # Take Profit target set down at the support floor
                pred_tp = static_support if static_support < pred_entry else pred_entry * 0.994
            
            # Mathematical extraction of absolute risk/reward profiles
            risk_amt = abs(pred_entry - pred_sl)
            reward_amt = abs(pred_tp - pred_entry)
            calculated_rr = reward_amt / risk_amt if risk_amt > 0 else 0.0
            
            # Define Trade Style Profile based on pattern geometries and targets
            if "WEDGE" in detected_pattern or "FLAG" in detected_pattern:
                assigned_style = "SCALPING PROFILE"
            elif "BOS" in structure_label:
                assigned_style = "DAY TRADING PROFILE"
            else:
                assigned_style = "SWING TRADING PROFILE"
            
            # Display stats to interface layout
            st.markdown(f"### 📊 Strategy Blueprint: **{assigned_style}** ({pred_direction})")
            
            col_ent, col_tp, col_sl, col_rr = st.columns(4)
            col_ent.metric("Suggested Entry POI", f"${pred_entry:.5f}")
            col_tp.metric("Take Profit Target (TP)", f"${pred_tp:.5f}")
            col_sl.metric("Structural Risk (SL)", f"${pred_sl:.5f}")
            
            if calculated_rr >= 2.0:
                col_rr.metric("Risk-to-Reward Ratio (R:R)", f"1 : {calculated_rr:.2f} ✅")
            else:
                col_rr.metric("Risk-to-Reward Ratio (R:R)", f"1 : {calculated_rr:.2f} ⚠️ (Sub-optimal)")
            
            if st.session_state.active_trade["status"] == "IDLE":
                if calculated_rr >= 2.0:
                    if st.button("🔒 Arm System & Lock Setup to Background Memory"):
                        st.session_state.active_trade = {
                            "status": "PENDING",
                            "ticker_label": selected_label,
                            "ticker_symbol": native_symbol,
                            "direction": pred_direction,
                            "entry_poi": pred_entry,
                            "sl": pred_sl,
                            "tp": pred_tp,
                            "rr_ratio": calculated_rr,
                            "trade_style": assigned_style,
                            "strategy_source": "Unified Multi-Strategy Engine"
                        }
                        st.success("Setup safely locked to state memory. The system radar is now frozen on this target.")
                        st.rerun()
                else:
                    st.error("🛑 System Lock Aborted: This setup does not offer a high-grade 1:2 Risk-to-Reward ratio. Let the market reset.")
            else:
                st.info(f"System memory locked. Release the active tracking lock from the sidebar to authorize a new trade profile scan.")
