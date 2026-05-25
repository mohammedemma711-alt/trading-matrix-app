import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np

# =====================================================================
# 📥 LAYER 1: MULTI-ASSET MARKET DATA ENGINE
# =====================================================================
class DataEngine:
    def __init__(self):
        self.ticker_map = {
            "XAUUSD (Gold)": "GC=F",
            "GBPUSD (Forex)": "GBPUSD=X",
            "USOIL (Crude Oil)": "CL=F",
            "BTCUSDT (Bitcoin)": "BTC-USD",
            "NAS100 (Nasdaq 100)": "^NDX"
        }

    def fetch_candles(self, user_symbol, interval="4h"):
        ticker = self.ticker_map.get(user_symbol)
        if not ticker: return None
        period = "60d" if interval == "4h" else "730d"
        try:
            asset = yf.Ticker(ticker)
            df = asset.history(period=period, interval=interval)
            if df.empty: return None
            df = df.reset_index()
            df = df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
            return df[['open', 'high', 'low', 'close', 'volume']]
        except:
            return None

# =====================================================================
# 🏦 LAYER 2: PREDICTIVE PRICE ACTION, SMC & FIBONACCI MATRIX ENGINE
# =====================================================================
class MasterTradingEngine:
    @staticmethod
    def identify_swings(df, window=7):
        highs = df['high'].values
        lows = df['low'].values
        swing_highs = []
        swing_lows = []
        
        for i in range(window, len(df) - window):
            if highs[i] == max(highs[i-window:i+window+1]):
                swing_highs.append((i, highs[i]))
            if lows[i] == min(lows[i-window:i+window+1]):
                swing_lows.append((i, lows[i]))
        return swing_highs, swing_lows

    @staticmethod
    def check_candle_confirmations(df):
        if len(df) < 3: return "NONE", 0
        c1, c2 = df.iloc[-2], df.iloc[-1]
        c1_body, c2_body, c2_total = abs(c1['close'] - c1['open']), abs(c2['close'] - c2['open']), c2['high'] - c2['low']
        
        if c2['close'] > c2['open'] and c1['close'] < c1['open'] and c2['close'] > c1['open'] and c2['open'] < c1['close']:
            return "BULLISH_ENGULFING", 3
        if c2['close'] < c2['open'] and c1['close'] > c1['open'] and c2['close'] < c1['open'] and c2['open'] > c1['close']:
            return "BEARISH_ENGULFING", 3
        if c2_total > 0:
            if (min(c2['open'], c2['close']) - c2['low']) / c2_total > 0.60 and (c2_body / c2_total) < 0.30:
                return "BULLISH_HAMMER", 3
            if (c2['high'] - max(c2['open'], c2['close'])) / c2_total > 0.60 and (c2_body / c2_total) < 0.30:
                return "BEARISH_SHOOTING_STAR", 3
        return "NONE", 0

    @staticmethod
    def analyze_market(df, style="Day Trade"):
        signals = []
        strategies_used = []
        metrics = {
            "support": None, "resistance": None, "order_block": None, 
            "breaker_block": None, "trendline_bias": "NEUTRAL", "pattern": None,
            "bos": False, "retest": False, "rejection": False, "bias": "NEUTRAL",
            "candle_pattern": "NONE", "candle_score": 0, "predicted_poi": None,
            "fib_618": None, "fib_382": None, "fib_786": None  
        }
        
        if len(df) < 30: return signals, strategies_used, metrics
        
        current_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        
        # 1. Candlestick Confirmations
        candle_pattern, candle_score = MasterTradingEngine.check_candle_confirmations(df)
        metrics["candle_pattern"] = candle_pattern
        metrics["candle_score"] = candle_score
        if candle_pattern != "NONE":
            signals.append(f"Candle Confirmation: {candle_pattern}")
            strategies_used.append("Candlestick Momentum Analysis")

        # 2. Base Support and Resistance Zones
        lookback = 30 if style == "Day Trade" else 90
        metrics["resistance"] = df['high'].tail(lookback).max()
        metrics["support"] = df['low'].tail(lookback).min()
        
        # 📐 Automated Fibonacci Grid Calculator
        high_anchor = metrics["resistance"]
        low_anchor = metrics["support"]
        price_range = high_anchor - low_anchor
        
        metrics["fib_382"] = high_anchor - (price_range * 0.382)
        metrics["fib_618"] = high_anchor - (price_range * 0.618)  
        metrics["fib_786"] = high_anchor - (price_range * 0.786)
        strategies_used.append("Automated Fibonacci Retracement Engine")
        
        # 3. Break & Retest
        if prev_price > metrics["resistance"] and current_price <= metrics["resistance"] * 1.003 and current_price >= metrics["resistance"] * 0.997:
            signals.append("Macro Break & Retest Setup")
            strategies_used.append("S/R Role Reversal Filter")
            metrics["retest"] = True
            metrics["bias"] = "LONG"
            
        # 4. Liquidity Rejections
        latest_candle = df.iloc[-1]
        body_size, total_size = abs(latest_candle['close'] - latest_candle['open']), latest_candle['high'] - latest_candle['low']
        if total_size > 0 and (body_size / total_size) < 0.25:
            if latest_candle['low'] <= metrics["support"] * 1.008:
                signals.append("Macro Liquidity Rejection Floor")
                strategies_used.append("Liquidity Pool Sweep Validation")
                metrics["rejection"] = True
                metrics["bias"] = "LONG"
            elif latest_candle['high'] >= metrics["resistance"] * 0.992:
                signals.append("Macro Liquidity Rejection Ceiling")
                strategies_used.append("Liquidity Pool Sweep Validation")
                metrics["rejection"] = True
                metrics["bias"] = "SHORT"

        # Structural Swings Mapping
        sh, sl = MasterTradingEngine.identify_swings(df)
        
        if len(sh) >= 3 and len(sl) >= 3:
            last_high_idx, last_high_val = sh[-1]
            last_low_idx, last_low_val = sl[-1]
            
            # 5. BOS Detection
            if current_price > last_high_val:
                signals.append("Market Structure Break (BOS - Bullish)")
                strategies_used.append("Market Structure Break (BOS)")
                metrics["bos"] = True
                metrics["bias"] = "LONG"
            elif current_price < last_low_val:
                signals.append("Market Structure Break (BOS - Bearish)")
                strategies_used.append("Market Structure Break (BOS)")
                metrics["bos"] = True
                metrics["bias"] = "SHORT"

            # 6. Order Blocks & Breakers
            if metrics["bos"] and metrics["bias"] == "LONG":
                metrics["order_block"] = df['low'].iloc[last_high_idx - 1]
                signals.append(f"Bullish Order Block at ${metrics['order_block']:,.2f}")
                strategies_used.append("Smart Money Order Block (OB) Mapping")
            if prev_price < last_low_val and current_price > last_low_val:
                metrics["breaker_block"] = last_low_val
                signals.append(f"Breaker Block Reclaimed at ${last_low_val:,.2f}")
                strategies_used.append("SMC Breaker Block (BB) Flipping")

            # 7. Double Tops & Bottoms
            if abs(sh[-1][1] - sh[-2][1]) / sh[-1][1] < 0.005:
                signals.append("Double Top Structure")
                strategies_used.append("Classical Retail Double Top Distribution")
                metrics["pattern"] = "DOUBLE_TOP"
                metrics["bias"] = "SHORT"
            elif abs(sl[-1][1] - sl[-2][1]) / sl[-1][1] < 0.005:
                signals.append("Double Bottom Structure")
                strategies_used.append("Classical Retail Double Bottom Accumulation")
                metrics["pattern"] = "DOUBLE_BOTTOM"
                metrics["bias"] = "LONG"

            # Slope Profiles
            x_highs, y_highs = [p[0] for p in sh[-3:]], [p[1] for p in sh[-3:]]
            slope_highs = np.polyfit(x_highs, y_highs, 1)[0]
            x_lows, y_lows = [p[0] for p in sl[-3:]], [p[1] for p in sl[-3:]]
            slope_lows = np.polyfit(x_lows, y_lows, 1)[0]
            
            metrics["trendline_bias"] = "BULLISH UPTREND" if slope_highs > 0 else "BEARISH DOWNTREND"

            # 8. Triangle Strategy Logic
            if slope_highs < -0.001 and slope_lows > 0.001:
                signals.append("Symmetrical Triangle Pattern Coil")
                strategies_used.append("Symmetrical Chart Coiling Geometry")
                metrics["pattern"] = "SYMMETRICAL_TRIANGLE"
            elif abs(slope_highs) < 0.002 and slope_lows > 0.002:
                signals.append("Bullish Ascending Triangle Pattern")
                strategies_used.append("Ascending Triangle Consolidation")
                metrics["pattern"] = "BULLISH_TRIANGLE"
                metrics["bias"] = "LONG"
            elif slope_highs < -0.002 and abs(slope_lows) < 0.002:
                signals.append("Bearish Descending Triangle Pattern")
                strategies_used.append("Descending Triangle Distribution")
                metrics["pattern"] = "BEARISH_TRIANGLE"
                metrics["bias"] = "SHORT"
            # 9. Flags & Wedges
            elif slope_highs > 0 and slope_lows > 0 and metrics["trendline_bias"] == "BULLISH UPTREND":
                signals.append("Bullish Flag Chart Pattern")
                strategies_used.append("Flag Trend Continuation")
                metrics["pattern"] = "BULLISH_FLAG"
                metrics["bias"] = "LONG"
            elif slope_highs < 0 and slope_lows < 0 and metrics["trendline_bias"] == "BEARISH DOWNTREND":
                signals.append("Bearish Flag Chart Pattern")
                strategies_used.append("Flag Trend Continuation")
                metrics["pattern"] = "BEARISH_FLAG"
                metrics["bias"] = "SHORT"

        # 🔮 PREDICTIVE POI HIGH-CONFLUENCE TARGETING LOOPS
        if metrics["bias"] == "LONG" or "BULLISH" in metrics["candle_pattern"]:
            if metrics["order_block"] and metrics["order_block"] < current_price:
                metrics["predicted_poi"] = metrics["order_block"]
            elif metrics["fib_618"] and metrics["fib_618"] < current_price:
                metrics["predicted_poi"] = metrics["fib_618"]
                signals.append("Confluence Match: 61.8% Golden Pocket Floor")
            else:
                metrics["predicted_poi"] = metrics["support"]
                
        elif metrics["bias"] == "SHORT" or "BEARISH" in metrics["candle_pattern"]:
            if metrics["breaker_block"] and metrics["breaker_block"] > current_price:
                metrics["predicted_poi"] = metrics["breaker_block"]
            elif metrics["fib_618"] and metrics["fib_618"] > current_price:
                metrics["predicted_poi"] = metrics["fib_618"]
                signals.append("Confluence Match: 61.8% Golden Pocket Ceiling")
            else:
                metrics["predicted_poi"] = metrics["resistance"]

        if candle_pattern != "NONE":
            metrics["bias"] = "LONG" if "BULLISH" in candle_pattern else "SHORT"

        return signals, list(set(strategies_used)), metrics

# =====================================================================
# 📊 LAYER 3: WORKSPACE SUITE & DYNAMIC LIVE MONITOR MEMORY INTERFACE
# =====================================================================
st.set_page_config(page_title="Predictive Strategy Suite", layout="wide", page_icon="🔮")
st.title("🔮 Predictive High-Timeframe Strategy Suite")
st.markdown("Advanced workspace calculating impending Point of Interest (POI) horizons with persistent trade monitoring.")
st.divider()

# --- INITIALIZE CORE ENGINE AND ACTIVE RADAR APP MEMORY ---
if 'engine' not in st.session_state:
    st.session_state.engine = DataEngine()

if 'active_position' not in st.session_state:
    st.session_state.active_position = {
        "status": "IDLE",       # IDLE, PENDING, CLOSED
        "asset": None,
        "bias": None,
        "poi": None,
        "entry": None,
        "sl": None,
        "tp": None,
        "style_label": None
    }

# --- CONTROL SYSTEM CONFIGURATIONS ---
st.sidebar.header("🎯 Campaign Settings")
trade_style = st.sidebar.radio("Select Trading System Horizon:", options=["Day Trade (4-Hour Windows)", "Swing Trade (Daily Windows)"])
target_pair = st.sidebar.selectbox("Select Target Market:", options=["XAUUSD (Gold)", "GBPUSD (Forex)", "USOIL (Crude Oil)", "BTCUSDT (Bitcoin)", "NAS100 (Nasdaq 100)"], index=0)
scan_button = st.sidebar.button("⚡ Run Predictive Scan", use_container_width=True)

# --- DYNAMIC BACKGROUND CONTINUOUS RADAR MONITOR ---
st.sidebar.divider()
st.sidebar.subheader("🛰️ Active Radar Tracker")
pos = st.session_state.active_position

if pos["status"] != "IDLE":
    st.sidebar.warning(f"🔒 SYSTEM LOCKED: Tracking {pos['style_label']} on {pos['asset']}")
    st.sidebar.markdown(f"• **Direction Bias:** `{pos['bias']}`")
    st.sidebar.markdown(f"• **Targeted POI:** `${pos['poi']:,.2f}`")
    st.sidebar.markdown(f"• **Stop Loss (SL):** `${pos['sl']:,.2f}`")
    st.sidebar.markdown(f"• **Take Profit (TP):** `${pos['tp']:,.2f}`")
    
    # Run active background candles check on 15m intervals to scan execution boundaries
    df_live = st.session_state.engine.fetch_candles(user_symbol=pos['asset'], interval="15m")
    if df_live is not None and not df_live.empty:
        live_price = df_live['close'].iloc[-1]
        st.sidebar.metric("Live Market Value", f"${live_price:,.2f}")
        
        # Continuously verify if target criteria have been violated or achieved
        if pos["bias"] == "LONG":
            if live_price <= pos["sl"]:
                st.session_state.active_position["status"] = "IDLE"
                st.sidebar.error("❌ Trade Closed: Stop Loss (SL) Breached.")
            elif live_price >= pos["tp"]:
                st.session_state.active_position["status"] = "IDLE"
                st.sidebar.success("🎯 Trade Closed: Take Profit (TP) Mitigated!")
        elif pos["bias"] == "SHORT":
            if live_price >= pos["sl"]:
                st.session_state.active_position["status"] = "IDLE"
                st.sidebar.error("❌ Trade Closed: Stop Loss (SL) Breached.")
            elif live_price <= pos["tp"]:
                st.session_state.active_position["status"] = "IDLE"
                st.sidebar.success("🎯 Trade Closed: Take Profit (TP) Mitigated!")
                
    if st.sidebar.button("🗑️ Reset Tracking Core"):
        st.session_state.active_position = {"status": "IDLE", "asset": None, "bias": None, "poi": None, "entry": None, "sl": None, "tp": None, "style_label": None}
        st.rerun()
else:
    st.sidebar.info("System scan radar is wide open. Select an asset and initiate a scan to allocate parameters.")

# --- ANALYTICAL COMPUTATION RUN LAYER ---
if scan_button or 'first_run' not in st.session_state:
    st.session_state.first_run = True
    main_interval = "4h" if trade_style == "Day Trade (4-Hour Windows)" else "1d"
    
    with st.spinner(f"Mapping predictive matrix levels for {target_pair}..."):
        df_chart = st.session_state.engine.fetch_candles(user_symbol=target_pair, interval=main_interval)

    if df_chart is not None:
        style_label = "Day Trade" if "Day" in trade_style else "Swing Trade"
        all_signals, strategies_used, metrics = MasterTradingEngine.analyze_market(df_chart, style=style_label)
        
        current_price = df_chart['close'].iloc[-1]
        master_bias = metrics["bias"]
        predicted_poi = metrics["predicted_poi"]

        # --- PREDICTIVE DISPLAY MATRIX ---
        st.subheader("🔮 Impending Point of Interest (POI) Radar")
        if predicted_poi:
            distance = abs(current_price - predicted_poi)
            pct_distance = (distance / current_price) * 100
            
            p_col1, p_col2, p_col3 = st.columns([1.5, 1, 2.5])
            p_col1.metric("PREDICTED POI TARGET ZONE", f"${predicted_poi:,.2f}", help="The system calculated this macro boundary line ahead of time.")
            p_col2.metric("DISTANCE TO ZONE", f"{pct_distance:.2f}% Away", delta=f"${distance:,.2f} remaining")
            
            with p_col3:
                st.markdown("**🧠 Active Strategies Engine Is Currently Using to Determine This POI:**")
                if strategies_used:
                    for strat in strategies_used:
                        st.markdown(f"✅ ` {strat} `")
                else:
                    st.markdown("• Core structural support/resistance horizon bounds.")
        else:
            st.info("System is waiting for a clear directional swing anchor to generate a forward-looking POI path.")

        st.divider()

        # --- TARGET METRIC WRITING MATRIX BLOCK ---
        st.subheader(f"🎯 Definitive {style_label} Execution Output")
        
        # Build strict institutional fallback targets safely before entering conditional visualization logic
        calc_sl = df_chart['low'].tail(3).min() * 0.998 if master_bias == "LONG" else df_chart['high'].tail(3).max() * 1.002
        calc_tp = current_price + ((current_price - calc_sl) * 3.0) if master_bias == "LONG" else current_price - ((calc_sl - current_price) * 3.0)

        if len(all_signals) >= 2 and master_bias != "NEUTRAL" and metrics["candle_pattern"] != "NONE":
            if master_bias == "LONG":
                st.success(f"### 🟢 {style_label.upper()} VERDICT: BUY / LONG POSITION VALIDATED")
            else:
                st.error(f"### 🔴 {style_label.upper()} VERDICT: SELL / SHORT POSITION VALIDATED")

            st.markdown("#### 📝 Comprehensive Reason for Trade:")
            narrative = f"A high-probability execution sequence is active on the {main_interval} chart for {target_pair}. The macro trend structure is tracing a **{metrics['trendline_bias']}** signature. "
            narrative += f"Our matrix has established severe structural confluence via: {', '.join(all_signals)}. "
            narrative += f"Institutional orders have been validated by a confirmed **{metrics['candle_pattern']}** closing pattern, proving that counter-retail positions have been successfully mitigated."
            st.markdown(f"> *{narrative}*")
            
            st.markdown("---")
            
            exec_col1, exec_col2, exec_col3, exec_col4 = st.columns(4)
            exec_col1.metric("POINT OF INTEREST (POI)", f"${predicted_poi:,.2f}")
            exec_col2.metric("MARKET ENTRY PRICE", f"${current_price:,.2f}")
            exec_col3.metric("SWING STOP LOSS (SL)", f"${calc_sl:,.2f}")
            exec_col4.metric("TARGET TAKE PROFIT (TP)", f"${calc_tp:,.2f}")
            
            # --- ARMED TRIGGER ROUTER INTERFACE BUTTON ---
            if st.session_state.active_position["status"] == "IDLE":
                st.write("")
                if st.button("🔒 Arm Radar to Monitor This Setup Live", use_container_width=True):
                    st.session_state.active_position = {
                        "status": "PENDING",
                        "asset": target_pair,
                        "bias": master_bias,
                        "poi": predicted_poi,
                        "entry": current_price,
                        "sl": calc_sl,
                        "tp": calc_tp,
                        "style_label": style_label
                    }
                    st.success("Target parameters successfully locked into tracking memory framework.")
                    st.rerun()
            
        else:
            st.warning("### 💤 SYSTEM FILTER ACTIVE: PRICE OUTSIDE OPTIMAL EXECUTION GATE")
            st.markdown(f"**Current Status:** The asset is tracking toward the calculated POI zone of **${predicted_poi:,.2f}**. No entry values will print under this block until the market successfully reaches this zone and registers an official confirmation candle signature.")

        st.divider()

        # --- CHECKLIST SYSTEMS VIEW OVERVIEWS ---
        st.subheader("🔍 Active Strategy Monitor Checklist")
        check_col1, check_col2 = st.columns(2)
        with check_col1:
            st.info("📊 **Retail Price Action & Fibonacci Grid**")
            st.markdown(f"• **Major Support Level Floor:** ${metrics['support']:,.2f}")
            st.markdown(f"• **Major Resistance Level Ceiling:** ${metrics['resistance']:,.2f}")
            st.markdown(f"• 📉 **Fibonacci 38.2% Line:** ${metrics['fib_382']:,.2f}")
            st.markdown(f"• 🔥 **Fibonacci 61.8% Golden Pocket:** ${metrics['fib_618']:,.2f}")
            st.markdown(f"• 🛑 **Fibonacci 78.6% Line:** ${metrics['fib_786']:,.2f}")
            st.markdown(f"• **Trendline Axis Environment:** `{metrics['trendline_bias']}`")
            st.markdown(f"• **Active Geometric Pattern:** `{metrics['pattern'] if metrics['pattern'] else 'NONE'}`")
            st.markdown(f"• **Break & Retest Verified:** `{'YES' if metrics['retest'] else 'NO'}`")
            
        with check_col2:
            st.success("🏦 **Smart Money & Candle Confirmation**")
            st.markdown(f"• **🚨 CANDLE CONFIRMATION SIGNATURE:** `{metrics['candle_pattern']}`")
            st.markdown(f"• **BOS (Break of Structure):** `{'CONFIRMED' if metrics['bos'] else 'NO CHANGE'}`")
            st.markdown(f"• **Active Order Block Zone:** " + (f"`${metrics['order_block']:,.2f}`" if metrics['order_block'] else "`NONE`"))
            st.markdown(f"• **Active Breaker Block Level:** " + (f"`${metrics['breaker_block']:,.2f}`" if metrics['breaker_block'] else "`NONE`"))
            st.markdown(f"• **Wick Liquidity Rejection:** `{'DETECTED' if metrics['rejection'] else 'NONE'}`")

    else:
        st.error("Market data feed is temporarily resting. Note: Traditional markets like Gold, Oil, Forex, and the Nasdaq index do not tick on weekends!")
