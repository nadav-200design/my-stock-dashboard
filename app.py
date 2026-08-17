import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import scipy

# Page Configuration
st.set_page_config(page_title="Market Intelligence Dashboard", layout="wide", page_icon="📈")

# --- Custom CSS ---
st.markdown("""
<style>
    .kpi-card {
        background-color: #1E1E1E;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #333;
        margin-bottom: 1rem;
    }
    .kpi-title {
        color: #888;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    .kpi-value {
        color: #FFF;
        font-size: 1.5rem;
        font-weight: bold;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- Utility Functions ---
def safe_float(val, default=0.0):
    try:
        return float(val) if pd.notnull(val) else default
    except (ValueError, TypeError):
        return default

def safe_metric(val, format_str="${:,.2f}"):
    if val is None or pd.isna(val) or val == "N/A":
         return "N/A"
    try:
         return format_str.format(float(val))
    except (ValueError, TypeError):
         return "N/A"

def format_large_number(num):
    if num is None or pd.isna(num) or num == "N/A": return "N/A"
    try:
        num = float(num)
        if num >= 1e12: return f"${num/1e12:.2f}T"
        if num >= 1e9: return f"${num/1e9:.2f}B"
        if num >= 1e6: return f"${num/1e6:.2f}M"
        return f"${num:.2f}"
    except:
        return "N/A"

# --- Data Fetching & Caching ---
@st.cache_data(ttl=3600)
def fetch_stock_data(ticker, period, interval):
    try:
        tkr = yf.Ticker(ticker)
        df = tkr.history(period=period, interval=interval)
        if df.empty:
            return pd.DataFrame()
        return df.reset_index()
    except Exception as e:
        st.error(f"Error fetching historical data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_market_pulse():
    indices = {"^GSPC": "S&P 500", "^IXIC": "Nasdaq", "^VIX": "VIX"}
    data = {}
    try:
        for symbol, name in indices.items():
            tkr = yf.Ticker(symbol)
            hist = tkr.history(period="5d")
            if len(hist) >= 2:
                last_close = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2]
                pct_change = ((last_close - prev_close) / prev_close) * 100
                data[name] = {"price": last_close, "change": pct_change}
            else:
                data[name] = {"price": None, "change": None}
    except Exception as e:
        pass
    return data

@st.cache_data(ttl=3600)
def fetch_company_info(ticker):
    try:
        tkr = yf.Ticker(ticker)
        return tkr.info or {}
    except Exception as e:
        st.error(f"Error fetching company info: {e}")
        return {}

@st.cache_data(ttl=3600)
def fetch_financials(ticker):
    try:
        tkr = yf.Ticker(ticker)
        return tkr.financials if tkr.financials is not None else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_balance_sheet(ticker):
    try:
        tkr = yf.Ticker(ticker)
        return tkr.balance_sheet if tkr.balance_sheet is not None else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_cashflow(ticker):
    try:
        tkr = yf.Ticker(ticker)
        return tkr.cashflow if tkr.cashflow is not None else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# --- Top Banner: Market Pulse ---
pulse_data = fetch_market_pulse()
if pulse_data:
    cols = st.columns(len(pulse_data))
    for i, (name, metrics) in enumerate(pulse_data.items()):
        with cols[i]:
            if metrics["price"] is not None:
                st.metric(name, f"{metrics['price']:.2f}", f"{metrics['change']:.2f}%")
            else:
                st.metric(name, "N/A", "N/A")
st.divider()

# --- Sidebar & Watchlist Control ---
st.sidebar.header("Market Intelligence Control")

# Preset buttons
st.sidebar.write("Popular Tickers")
preset_tickers = ["AAPL", "NVDA", "MSFT", "AMZN", "GOOGL", "TSLA"]
preset_cols = st.sidebar.columns(3)
selected_preset = None
for i, pt in enumerate(preset_tickers):
    if preset_cols[i % 3].button(pt):
        selected_preset = pt

# Ticker Input
ticker_input = st.sidebar.text_input("Search Ticker", value=selected_preset if selected_preset else "AAPL").upper()
ticker_symbol = ticker_input

# Timeframe & Resolution
time_periods = ["1M", "3M", "6M", "1Y", "2Y", "5Y", "MAX"]
yf_periods = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "2Y": "2y", "5Y": "5y", "MAX": "max"}
selected_period = st.sidebar.selectbox("Timeframe", time_periods, index=3)

intervals = ["1d", "1wk", "1mo"]
selected_interval = st.sidebar.selectbox("Interval", intervals, index=0)

# --- Main Interface Tabs ---
tab_tech, tab_fund, tab_stmts, tab_health = st.tabs([
    "📈 Advanced Technical Terminal",
    "📊 Fundamental & Valuation Engine",
    "📑 Financial Statements Deep Dive",
    "🛡️ Financial Health & Quality Scores"
])

# --- Tab 1: 📈 Advanced Technical Terminal ---
with tab_tech:
    df = fetch_stock_data(ticker_symbol, yf_periods[selected_period], selected_interval)

    if not df.empty:
        # Date column handling (yf might return Date or Datetime)
        date_col = 'Date' if 'Date' in df.columns else 'Datetime' if 'Datetime' in df.columns else df.columns[0]

        # Calculate Technical Indicators
        # MAs
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA_100'] = df['Close'].ewm(span=100, adjust=False).mean()
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

        # Bollinger Bands (20, 2)
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['BB_Std'] = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['SMA_20'] + (df['BB_Std'] * 2)
        df['BB_Lower'] = df['SMA_20'] - (df['BB_Std'] * 2)

        # VWAP
        q = df['Volume'].values
        p = (df['High'] + df['Low'] + df['Close']).values / 3
        df['VWAP'] = np.cumsum(p * q) / np.cumsum(q)
        df['VWAP'] = df['VWAP'].bfill() # handle initial NAs

        # RSI (14)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # MACD (12, 26, 9)
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['Signal_Line']

        # Stochastic Oscillator (%K, %D)
        low_14 = df['Low'].rolling(window=14).min()
        high_14 = df['High'].rolling(window=14).max()
        df['%K'] = 100 * ((df['Close'] - low_14) / (high_14 - low_14))
        df['%D'] = df['%K'].rolling(window=3).mean()

        # Volume Color
        df['Vol_Color'] = np.where(df['Close'] >= df['Open'], 'rgba(0, 255, 0, 0.5)', 'rgba(255, 0, 0, 0.5)')

        # Subplot Selection (ATR vs Stoch)
        st.subheader("Chart Controls")
        col_ctrl1, col_ctrl2 = st.columns(2)
        with col_ctrl1:
            show_emas = st.checkbox("Show EMA Ribbon (20, 50, 100, 200)", value=True)
            show_bb = st.checkbox("Show Bollinger Bands", value=False)
            show_vwap = st.checkbox("Show VWAP", value=False)
        with col_ctrl2:
            bottom_panel = st.radio("Bottom Panel Indicator", ["Stochastic Oscillator", "Average True Range (ATR)"], horizontal=True)

        if bottom_panel == "Average True Range (ATR)":
             tr1 = df['High'] - df['Low']
             tr2 = abs(df['High'] - df['Close'].shift(1))
             tr3 = abs(df['Low'] - df['Close'].shift(1))
             df['TR'] = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
             df['ATR'] = df['TR'].rolling(window=14).mean()

        # Build Plotly Figure
        fig = make_subplots(
            rows=4, cols=1, shared_xaxes=True,
            vertical_spacing=0.02,
            row_heights=[0.55, 0.15, 0.15, 0.15],
            subplot_titles=("Price & Overlays", "Volume & MACD", "RSI (14)", bottom_panel)
        )

        # 1. Main Chart
        fig.add_trace(go.Candlestick(
            x=df[date_col], open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'], name='Price',
            increasing_line_color='#26a69a', decreasing_line_color='#ef5350'
        ), row=1, col=1)

        if show_emas:
            fig.add_trace(go.Scatter(x=df[date_col], y=df['EMA_20'], line=dict(color='#2962FF', width=1), name='EMA 20'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df[date_col], y=df['EMA_50'], line=dict(color='#FF6D00', width=1), name='EMA 50'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df[date_col], y=df['EMA_100'], line=dict(color='#00C853', width=1), name='EMA 100'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df[date_col], y=df['EMA_200'], line=dict(color='#D50000', width=1), name='EMA 200'), row=1, col=1)

        if show_bb:
            fig.add_trace(go.Scatter(x=df[date_col], y=df['BB_Upper'], line=dict(color='rgba(255,255,255,0.2)'), name='BB Upper', showlegend=False), row=1, col=1)
            fig.add_trace(go.Scatter(x=df[date_col], y=df['BB_Lower'], line=dict(color='rgba(255,255,255,0.2)'), fill='tonexty', fillcolor='rgba(255,255,255,0.05)', name='BB Channel', showlegend=False), row=1, col=1)

        if show_vwap:
            fig.add_trace(go.Scatter(x=df[date_col], y=df['VWAP'], line=dict(color='#FFD600', width=1.5, dash='dash'), name='VWAP'), row=1, col=1)

        # 2. Volume & MACD Overlay
        fig.add_trace(go.Bar(x=df[date_col], y=df['Volume'], marker_color=df['Vol_Color'], name='Volume', opacity=0.5, yaxis='y5'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df[date_col], y=df['MACD'], line=dict(color='#2962FF', width=1), name='MACD'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df[date_col], y=df['Signal_Line'], line=dict(color='#FF6D00', width=1), name='Signal'), row=2, col=1)
        fig.add_trace(go.Bar(x=df[date_col], y=df['MACD_Hist'], marker_color=np.where(df['MACD_Hist']>=0, '#26a69a', '#ef5350'), name='MACD Hist'), row=2, col=1)

        # 3. RSI
        fig.add_trace(go.Scatter(x=df[date_col], y=df['RSI'], line=dict(color='#E040FB', width=1.5), name='RSI'), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ef5350", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#26a69a", row=3, col=1)

        # 4. Bottom Panel
        if bottom_panel == "Stochastic Oscillator":
            fig.add_trace(go.Scatter(x=df[date_col], y=df['%K'], line=dict(color='#2962FF', width=1.5), name='%K'), row=4, col=1)
            fig.add_trace(go.Scatter(x=df[date_col], y=df['%D'], line=dict(color='#FF6D00', width=1.5), name='%D'), row=4, col=1)
            fig.add_hline(y=80, line_dash="dash", line_color="#ef5350", row=4, col=1)
            fig.add_hline(y=20, line_dash="dash", line_color="#26a69a", row=4, col=1)
        else:
            fig.add_trace(go.Scatter(x=df[date_col], y=df['ATR'], line=dict(color='#00B0FF', width=1.5), name='ATR'), row=4, col=1)

        # Update Layout
        fig.update_layout(
            template='plotly_dark',
            height=900,
            xaxis_rangeslider_visible=False,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=30, b=10)
        )
        fig.update_xaxes(rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # Key Pivot Levels & 52w
        st.subheader("Key Price Levels")
        recent_high = df['High'].max()
        recent_low = df['Low'].min()

        last_close = df['Close'].iloc[-1]
        last_high = df['High'].iloc[-1]
        last_low = df['Low'].iloc[-1]

        pivot = (last_high + last_low + last_close) / 3
        r1 = (2 * pivot) - last_low
        s1 = (2 * pivot) - last_high
        r2 = pivot + (last_high - last_low)
        s2 = pivot - (last_high - last_low)

        pcol1, pcol2, pcol3, pcol4, pcol5, pcol6, pcol7 = st.columns(7)
        pcol1.metric("52W High", f"${recent_high:.2f}")
        pcol2.metric("R2", f"${r2:.2f}")
        pcol3.metric("R1", f"${r1:.2f}")
        pcol4.metric("Pivot", f"${pivot:.2f}")
        pcol5.metric("S1", f"${s1:.2f}")
        pcol6.metric("S2", f"${s2:.2f}")
        pcol7.metric("52W Low", f"${recent_low:.2f}")

    else:
        st.warning(f"No historical price data found for {ticker_symbol}.")

# --- Tab 2: 📊 Fundamental & Valuation Engine ---
with tab_fund:
    info = fetch_company_info(ticker_symbol)

    st.subheader("Summary Valuation KPIs")
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)

    kpi_col1.metric("Market Cap", format_large_number(info.get('marketCap')))
    kpi_col2.metric("Enterprise Value", format_large_number(info.get('enterpriseValue')))
    kpi_col3.metric("Trailing P/E", safe_metric(info.get('trailingPE'), "{:.2f}x"))
    kpi_col4.metric("Forward P/E", safe_metric(info.get('forwardPE'), "{:.2f}x"))
    kpi_col5.metric("PEG Ratio", safe_metric(info.get('pegRatio'), "{:.2f}"))

    kpi_col6, kpi_col7, kpi_col8, kpi_col9, kpi_col10 = st.columns(5)
    kpi_col6.metric("EV/EBITDA", safe_metric(info.get('enterpriseToEbitda'), "{:.2f}x"))
    kpi_col7.metric("Price-to-FCF", safe_metric(info.get('priceToFreeCashFlows') or (info.get('marketCap')/info.get('freeCashflow') if info.get('freeCashflow') else None), "{:.2f}x"))
    kpi_col8.metric("Price-to-Book", safe_metric(info.get('priceToBook'), "{:.2f}x"))
    div_y = info.get('dividendYield')
    kpi_col9.metric("Div Yield", f"{div_y*100:.2f}%" if div_y else "N/A")
    kpi_col10.metric("Current Price", safe_metric(info.get('currentPrice'), "${:.2f}"))

    st.divider()

    st.subheader("Multi-Model Valuation Calculator")

    # Try to get default values for valuation
    cf = fetch_cashflow(ticker_symbol)
    latest_fcf = 0.0
    if not cf.empty and 'Free Cash Flow' in cf.index:
        latest_fcf = safe_float(cf.loc['Free Cash Flow'].iloc[0])
    elif info.get('freeCashflow'):
        latest_fcf = safe_float(info.get('freeCashflow'))

    eps_ttm = safe_float(info.get('trailingEps'), 0.0)
    current_price = safe_float(info.get('currentPrice'), 0.0)
    shares_out = safe_float(info.get('sharesOutstanding'), 1.0)

    val_exp = st.expander("Valuation Inputs & Settings", expanded=True)
    with val_exp:
        vc1, vc2, vc3 = st.columns(3)
        # DCF Inputs
        fcf_input = vc1.number_input("Base Free Cash Flow ($)", value=float(latest_fcf), format="%.0f", help="Starting FCF for Year 0")
        wacc = vc2.number_input("Discount Rate (WACC) %", value=9.0, step=0.5) / 100
        growth = vc3.number_input("Expected Growth Rate % (Years 1-5)", value=10.0, step=0.5) / 100

        term_growth = vc1.number_input("Terminal Growth Rate %", value=2.5, step=0.1) / 100
        proj_years = vc2.number_input("Forecast Years", value=5, min_value=1, max_value=10)
        shares_input = vc3.number_input("Shares Outstanding", value=float(shares_out), format="%.0f")

        # Graham Inputs
        graham_growth = vc1.number_input("Graham Expected Growth %", value=growth*100, step=0.5)
        graham_eps = vc2.number_input("Graham EPS ($)", value=float(eps_ttm), step=0.1)
        bond_yield = vc3.number_input("Current Corp Bond Yield % (Y)", value=4.4, step=0.1)

    val_res1, val_res2, val_res3 = st.columns(3)

    # 1. DCF Model
    with val_res1:
        st.markdown("#### Discounted Cash Flow (DCF)")
        if wacc > term_growth and shares_input > 0:
            cash_flows = [fcf_input * (1 + growth)**i for i in range(1, proj_years + 1)]
            pv_cfs = sum([cf / (1 + wacc)**i for i, cf in enumerate(cash_flows, 1)])
            term_val = (cash_flows[-1] * (1 + term_growth)) / (wacc - term_growth)
            pv_term = term_val / (1 + wacc)**proj_years
            dcf_equity_val = pv_cfs + pv_term
            dcf_price = dcf_equity_val / shares_input

            st.metric("DCF Intrinsic Value", f"${dcf_price:.2f}")
            if current_price > 0:
                margin = (dcf_price - current_price) / current_price
                st.write(f"Margin of Safety: **{margin*100:.2f}%**")
        else:
            st.warning("Invalid DCF params (WACC <= Term Growth or zero shares)")

    # 2. Reverse DCF
    with val_res2:
        st.markdown("#### Reverse DCF")
        if current_price > 0 and shares_input > 0 and fcf_input > 0 and wacc > term_growth:
            market_equity = current_price * shares_input

            # Simple numeric solver for implied growth
            from scipy.optimize import fsolve
            def reverse_dcf_eq(g):
                cfs = [fcf_input * (1 + g[0])**i for i in range(1, proj_years + 1)]
                pv = sum([c / (1 + wacc)**i for i, c in enumerate(cfs, 1)])
                tv = (cfs[-1] * (1 + term_growth)) / (wacc - term_growth)
                ptv = tv / (1 + wacc)**proj_years
                return (pv + ptv) - market_equity

            try:
                implied_g = fsolve(reverse_dcf_eq, [0.05])[0]
                st.metric("Implied Growth Rate", f"{implied_g*100:.2f}%")
                st.write("Growth rate priced into the current stock price.")
            except:
                st.write("N/A (Solver failed)")
        else:
            st.write("N/A (Need positive Current Price and FCF)")

    # 3. Benjamin Graham
    with val_res3:
        st.markdown("#### Benjamin Graham Formula")
        if graham_eps > 0 and bond_yield > 0:
            # V = EPS * (8.5 + 2g) * 4.4 / Y
            graham_value = graham_eps * (8.5 + 2 * graham_growth) * 4.4 / bond_yield
            st.metric("Graham Intrinsic Value", f"${graham_value:.2f}")
            if current_price > 0:
                g_margin = (graham_value - current_price) / current_price
                st.write(f"Margin of Safety: **{g_margin*100:.2f}%**")
        else:
            st.write("N/A (Requires positive EPS and Bond Yield)")

    # Sensitivity Matrix
    st.markdown("#### DCF Sensitivity Matrix: Discount Rate vs Growth Rate")
    if wacc > term_growth and shares_input > 0:
        wacc_range = [wacc - 0.02, wacc - 0.01, wacc, wacc + 0.01, wacc + 0.02]
        growth_range = [growth - 0.04, growth - 0.02, growth, growth + 0.02, growth + 0.04]

        matrix_data = []
        for g in growth_range:
            row = []
            for w in wacc_range:
                if w > term_growth:
                    cfs = [fcf_input * (1 + g)**i for i in range(1, proj_years + 1)]
                    pv = sum([c / (1 + w)**i for i, c in enumerate(cfs, 1)])
                    tv = (cfs[-1] * (1 + term_growth)) / (w - term_growth)
                    ptv = tv / (1 + w)**proj_years
                    price = (pv + ptv) / shares_input
                    row.append(f"${price:.2f}")
                else:
                    row.append("N/A")
            matrix_data.append(row)

        sens_df = pd.DataFrame(matrix_data,
                               index=[f"Growth {g*100:.1f}%" for g in growth_range],
                               columns=[f"WACC {w*100:.1f}%" for w in wacc_range])
        st.dataframe(sens_df, use_container_width=True)

# --- Tab 3: 📑 Financial Statements Deep Dive ---
with tab_stmts:
    st.subheader("Historical Financial Data (4-Year)")

    fin = fetch_financials(ticker_symbol)
    bs = fetch_balance_sheet(ticker_symbol)
    cf = fetch_cashflow(ticker_symbol)

    if not fin.empty:
        # Chart: Revenue vs Net Income
        rev_row = fin.loc['Total Revenue'] if 'Total Revenue' in fin.index else None
        ni_row = fin.loc['Net Income'] if 'Net Income' in fin.index else None

        if rev_row is not None and ni_row is not None:
            rev_df = rev_row.to_frame(name='Total Revenue').reset_index()
            rev_df = rev_df.rename(columns={'index': 'Date'})
            ni_df = ni_row.to_frame(name='Net Income').reset_index()
            ni_df = ni_df.rename(columns={'index': 'Date'})

            chart_df = pd.merge(rev_df, ni_df, on='Date').sort_values('Date')

            fig_stmt = go.Figure()
            fig_stmt.add_trace(go.Bar(x=chart_df['Date'], y=chart_df['Total Revenue'], name='Total Revenue', marker_color='#2962FF'))
            fig_stmt.add_trace(go.Bar(x=chart_df['Date'], y=chart_df['Net Income'], name='Net Income', marker_color='#00C853'))

            fig_stmt.update_layout(title="Revenue vs Net Income Trend", template='plotly_dark', barmode='group')
            st.plotly_chart(fig_stmt, use_container_width=True)

    # Data Tables
    st_cols = st.columns(3)

    def display_stmt(df_stmt, title):
        st.markdown(f"**{title}**")
        if not df_stmt.empty:
            # Keep top rows, transpose to standard format
            clean_df = df_stmt.head(15).astype(str)
            st.dataframe(clean_df, use_container_width=True)
            csv = clean_df.to_csv()
            st.download_button(label=f"Download {title} CSV", data=csv, file_name=f"{ticker_symbol}_{title}.csv", mime="text/csv")
        else:
            st.write("Data Not Available")

    with st_cols[0]: display_stmt(fin, "Income Statement")
    with st_cols[1]: display_stmt(bs, "Balance Sheet")
    with st_cols[2]: display_stmt(cf, "Cash Flow Statement")

# --- Tab 4: 🛡️ Financial Health & Quality Scores ---
with tab_health:
    st.subheader("Financial Quality Assessment")

    fin = fetch_financials(ticker_symbol)
    bs = fetch_balance_sheet(ticker_symbol)
    cf = fetch_cashflow(ticker_symbol)

    hq_col1, hq_col2 = st.columns(2)

    # 1. Piotroski F-Score (Best effort with available data)
    with hq_col1:
        st.markdown("#### Piotroski F-Score")
        f_score = 0
        score_details = []

        try:
            # Profitability
            roa_curr = roa_prev = cfo_curr = 0
            if not fin.empty and not bs.empty:
                if 'Net Income' in fin.index and 'Total Assets' in bs.index:
                    ni = fin.loc['Net Income']
                    ta = bs.loc['Total Assets']
                    if len(ni) >= 2 and len(ta) >= 2:
                        roa_curr = ni.iloc[0] / ta.iloc[0]
                        roa_prev = ni.iloc[1] / ta.iloc[1]
                        if roa_curr > 0: f_score += 1; score_details.append("✅ Positive ROA")
                        else: score_details.append("❌ Negative ROA")

                        if roa_curr > roa_prev: f_score += 1; score_details.append("✅ ROA higher than previous year")
                        else: score_details.append("❌ ROA lower than previous year")

            if not cf.empty and 'Operating Cash Flow' in cf.index:
                cfo = cf.loc['Operating Cash Flow']
                if len(cfo) >= 1:
                    cfo_curr = cfo.iloc[0]
                    if cfo_curr > 0: f_score += 1; score_details.append("✅ Positive Operating Cash Flow")
                    else: score_details.append("❌ Negative Operating Cash Flow")

            if cfo_curr > 0 and 'Total Assets' in bs.index and len(bs.loc['Total Assets']) >= 1:
                ta_curr = bs.loc['Total Assets'].iloc[0]
                if (cfo_curr / ta_curr) > roa_curr: f_score += 1; score_details.append("✅ CFO > Net Income")
                else: score_details.append("❌ CFO < Net Income")

            # Note: Leverage, Liquidity, Operating Efficiency metrics require more specific keys which yfinance sometimes omits or renames.
            # We provide the base framework.

            st.metric("Estimated F-Score", f"{f_score} / 9" if score_details else "N/A")
            for d in score_details:
                st.write(d)
            st.caption("Note: Score is estimated based on available yfinance fields. A score of 8-9 is excellent, 0-2 is poor.")

        except Exception as e:
            st.write("Insufficient data to calculate F-Score.")

    # 2. DuPont Analysis
    with hq_col2:
        st.markdown("#### DuPont Analysis")
        try:
            if not fin.empty and not bs.empty:
                ni = safe_float(fin.loc['Net Income'].iloc[0]) if 'Net Income' in fin.index else 0
                rev = safe_float(fin.loc['Total Revenue'].iloc[0]) if 'Total Revenue' in fin.index else 1
                ta = safe_float(bs.loc['Total Assets'].iloc[0]) if 'Total Assets' in bs.index else 1
                te = safe_float(bs.loc['Total Stockholder Equity'].iloc[0]) if 'Total Stockholder Equity' in bs.index else (safe_float(bs.loc['Stockholders Equity'].iloc[0]) if 'Stockholders Equity' in bs.index else 1)

                net_profit_margin = ni / rev if rev else 0
                asset_turnover = rev / ta if ta else 0
                equity_multiplier = ta / te if te else 0

                roe = net_profit_margin * asset_turnover * equity_multiplier

                st.metric("Return on Equity (ROE)", f"{roe*100:.2f}%")
                st.write(f"- **Net Profit Margin:** {net_profit_margin*100:.2f}%")
                st.write(f"- **Asset Turnover:** {asset_turnover:.2f}x")
                st.write(f"- **Equity Multiplier:** {equity_multiplier:.2f}x")
            else:
                st.write("Insufficient data for DuPont Analysis.")
        except:
            st.write("Data parsing error for DuPont.")

    st.divider()

    # 3. Margins
    st.markdown("#### Margin Analysis")
    m1, m2, m3, m4 = st.columns(4)
    info = fetch_company_info(ticker_symbol)

    m1.metric("Gross Margin", f"{safe_float(info.get('grossMargins'))*100:.2f}%" if info.get('grossMargins') else "N/A")
    m2.metric("Operating Margin", f"{safe_float(info.get('operatingMargins'))*100:.2f}%" if info.get('operatingMargins') else "N/A")
    m3.metric("Net Margin", f"{safe_float(info.get('profitMargins'))*100:.2f}%" if info.get('profitMargins') else "N/A")
    m4.metric("Return on Assets", f"{safe_float(info.get('returnOnAssets'))*100:.2f}%" if info.get('returnOnAssets') else "N/A")
