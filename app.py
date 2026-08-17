import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# Page Configuration
st.set_page_config(page_title="Professional Stock Dashboard", layout="wide", page_icon="📈")

st.title("Professional Financial Dashboard")

# --- Data Fetching & Caching ---
@st.cache_data(ttl=3600)
def fetch_stock_data(ticker, period):
    try:
        tkr = yf.Ticker(ticker)
        df = tkr.history(period=period)
        if df.empty:
            return None
        return df.reset_index()
    except Exception as e:
        st.error(f"Error fetching historical data: {e}")
        return None

@st.cache_data(ttl=3600)
def fetch_company_info(ticker):
    try:
        tkr = yf.Ticker(ticker)
        return tkr.info
    except Exception as e:
        st.error(f"Error fetching company info: {e}")
        return {}

@st.cache_data(ttl=3600)
def fetch_financials(ticker):
    try:
        tkr = yf.Ticker(ticker)
        return tkr.financials
    except Exception as e:
        st.error(f"Error fetching financials: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_cashflow(ticker):
    try:
        tkr = yf.Ticker(ticker)
        return tkr.cashflow
    except Exception as e:
        st.error(f"Error fetching cashflow: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_news(ticker):
    try:
        tkr = yf.Ticker(ticker)
        return tkr.news
    except Exception as e:
        st.error(f"Error fetching news: {e}")
        return []

# --- Sidebar ---
st.sidebar.header("Dashboard Controls")
ticker_symbol = st.sidebar.text_input("Stock Ticker", value="AAPL").upper()

time_periods = {
    "1M": "1mo",
    "6M": "6mo",
    "1Y": "1y",
    "5Y": "5y",
    "MAX": "max"
}
selected_period = st.sidebar.selectbox("Time Period", list(time_periods.keys()), index=2)

theme_choice = st.sidebar.radio("Chart Theme", ("Dark Mode", "Light Mode"))
plotly_theme = "plotly_dark" if theme_choice == "Dark Mode" else "plotly_white"

# --- Main Interface Tabs ---
tab_tech, tab_fund, tab_overview = st.tabs([
    "📈 Technical Analysis",
    "📊 Fundamentals & Valuation",
    "🏢 Company Overview"
])

with tab_tech:
    st.header("Technical Analysis")

    if ticker_symbol:
        df = fetch_stock_data(ticker_symbol, time_periods[selected_period])

        if df is not None and not df.empty:
            # Controls for Technical Indicators
            st.subheader("Chart Options")
            col_opts1, col_opts2, col_opts3, col_opts4, col_opts5 = st.columns(5)
            with col_opts1:
                show_ema20 = st.checkbox("EMA 20", value=True)
            with col_opts2:
                show_sma50 = st.checkbox("SMA 50", value=True)
            with col_opts3:
                show_sma200 = st.checkbox("SMA 200", value=True)
            with col_opts4:
                show_custom_sma = st.checkbox("Custom SMA")
            with col_opts5:
                custom_sma_period = st.number_input("Custom Period", min_value=1, max_value=500, value=100, step=1, disabled=not show_custom_sma)

            # Calculate Moving Averages
            if show_ema20:
                df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
            if show_sma50:
                df['SMA_50'] = df['Close'].rolling(window=50).mean()
            if show_sma200:
                df['SMA_200'] = df['Close'].rolling(window=200).mean()
            if show_custom_sma:
                df[f'SMA_{custom_sma_period}'] = df['Close'].rolling(window=custom_sma_period).mean()

            # Calculate MACD
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = exp1 - exp2
            df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['MACD_Histogram'] = df['MACD'] - df['Signal_Line']

            # Calculate RSI (14)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            # Determine Volume Colors
            df['Color'] = np.where(df['Close'] >= df['Open'], 'green', 'red')

            # Create Subplots
            fig = make_subplots(
                rows=4, cols=1, shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.5, 0.15, 0.15, 0.2],
                subplot_titles=(f"{ticker_symbol} Price", "Volume", "MACD (12, 26, 9)", "RSI (14)")
            )

            # Row 1: Candlestick & MAs
            fig.add_trace(go.Candlestick(
                x=df['Date'], open=df['Open'], high=df['High'],
                low=df['Low'], close=df['Close'], name='Price'
            ), row=1, col=1)

            if show_ema20:
                fig.add_trace(go.Scatter(x=df['Date'], y=df['EMA_20'], line=dict(color='blue', width=1.5), name='EMA 20'), row=1, col=1)
            if show_sma50:
                fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_50'], line=dict(color='orange', width=1.5), name='SMA 50'), row=1, col=1)
            if show_sma200:
                fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_200'], line=dict(color='red', width=1.5), name='SMA 200'), row=1, col=1)
            if show_custom_sma:
                fig.add_trace(go.Scatter(x=df['Date'], y=df[f'SMA_{custom_sma_period}'], line=dict(color='purple', width=1.5, dash='dot'), name=f'SMA {custom_sma_period}'), row=1, col=1)

            # Row 2: Volume
            fig.add_trace(go.Bar(
                x=df['Date'], y=df['Volume'], name='Volume', marker_color=df['Color']
            ), row=2, col=1)

            # Row 3: MACD
            fig.add_trace(go.Scatter(x=df['Date'], y=df['MACD'], line=dict(color='blue', width=1.5), name='MACD'), row=3, col=1)
            fig.add_trace(go.Scatter(x=df['Date'], y=df['Signal_Line'], line=dict(color='orange', width=1.5), name='Signal'), row=3, col=1)
            fig.add_trace(go.Bar(x=df['Date'], y=df['MACD_Histogram'], name='Histogram', marker_color=np.where(df['MACD_Histogram']>=0, 'green', 'red')), row=3, col=1)

            # Row 4: RSI
            fig.add_trace(go.Scatter(x=df['Date'], y=df['RSI'], line=dict(color='purple', width=1.5), name='RSI'), row=4, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=4, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", row=4, col=1)

            # Layout Updates
            fig.update_layout(
                template=plotly_theme,
                height=900,
                xaxis_rangeslider_visible=False,
                xaxis4_rangeslider_visible=True, # Add range slider to bottom chart only
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            # Remove range sliders from upper charts to prevent visual clutter
            fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
            fig.update_xaxes(rangeslider_visible=False, row=2, col=1)
            fig.update_xaxes(rangeslider_visible=False, row=3, col=1)

            st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning("No historical price data found for the selected ticker and time period.")

with tab_fund:
    st.header("Fundamentals & Valuation")

    if ticker_symbol:
        info = fetch_company_info(ticker_symbol)

        # --- Key Metrics ---
        st.subheader("Key Metrics")
        col_m1, col_m2, col_m3 = st.columns(3)

        def format_large_number(num):
            if num is None or num == "N/A": return "N/A"
            try:
                num = float(num)
                if num >= 1e12: return f"${num/1e12:.2f}T"
                if num >= 1e9: return f"${num/1e9:.2f}B"
                if num >= 1e6: return f"${num/1e6:.2f}M"
                return f"${num:.2f}"
            except:
                return "N/A"

        with col_m1:
            st.metric("Market Cap", format_large_number(info.get('marketCap', 'N/A')))
            st.metric("Trailing P/E", round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else "N/A")
        with col_m2:
            st.metric("Forward P/E", round(info.get('forwardPE', 0), 2) if info.get('forwardPE') else "N/A")
            st.metric("EV/EBITDA", round(info.get('enterpriseToEbitda', 0), 2) if info.get('enterpriseToEbitda') else "N/A")
        with col_m3:
            st.metric("Price-to-Free-Cash-Flow", round(info.get('priceToFreeCashFlows', 0), 2) if info.get('priceToFreeCashFlows') else "N/A")
            div_yield = info.get('dividendYield')
            st.metric("Dividend Yield", f"{div_yield*100:.2f}%" if div_yield else "N/A")

        st.divider()

        # --- Financials ---
        st.subheader("Financial Statements (Last 4 Years)")
        financials = fetch_financials(ticker_symbol)
        cashflow = fetch_cashflow(ticker_symbol)

        col_fin1, col_fin2 = st.columns(2)
        with col_fin1:
            st.write("**Income Statement Summary**")
            if not financials.empty:
                # Transpose for easier reading (Dates as rows or columns depending on preference; keeping Dates as columns here is standard)
                st.dataframe(financials.head(10), use_container_width=True)
            else:
                st.write("No Income Statement data available.")

        with col_fin2:
            st.write("**Free Cash Flow Summary**")
            if not cashflow.empty:
                st.dataframe(cashflow.head(10), use_container_width=True)
            else:
                st.write("No Cash Flow data available.")

        st.divider()

        # --- DCF Valuation Estimator ---
        st.subheader("Interactive Quick DCF / Valuation Estimator")
        st.write("Estimate the intrinsic value of the company based on projected future cash flows.")

        # Try to pull latest Free Cash Flow
        latest_fcf = 0.0
        if not cashflow.empty and 'Free Cash Flow' in cashflow.index:
            try:
                latest_fcf = float(cashflow.loc['Free Cash Flow'].iloc[0])
            except:
                pass

        if latest_fcf <= 0:
            st.warning("Latest Free Cash Flow is zero or negative, making DCF challenging without manual adjustments.")

        col_dcf1, col_dcf2 = st.columns(2)
        with col_dcf1:
            current_fcf_input = st.number_input("Current Free Cash Flow (FCF) [$]", value=latest_fcf, format="%.0f")
            growth_rate = st.number_input("Expected Short-Term Growth Rate [%]", value=10.0, step=1.0) / 100.0
            projection_years = st.number_input("Projection Period [Years]", min_value=1, max_value=20, value=5, step=1)

        with col_dcf2:
            discount_rate = st.number_input("Discount Rate (WACC) [%]", value=9.0, step=0.5) / 100.0
            terminal_growth_rate = st.number_input("Terminal Growth Rate [%]", value=2.5, step=0.5) / 100.0
            shares_outstanding = info.get('sharesOutstanding', 1)
            shares_out_input = st.number_input("Shares Outstanding", value=float(shares_outstanding), format="%.0f")

        # DCF Calculation
        if st.button("Calculate Intrinsic Value"):
            try:
                future_cash_flows = []
                fcf = current_fcf_input

                # Project Cash Flows
                for year in range(1, projection_years + 1):
                    fcf *= (1 + growth_rate)
                    future_cash_flows.append(fcf)

                # Calculate PV of projected cash flows
                pv_future_cash_flows = sum([cf / ((1 + discount_rate) ** idx) for idx, cf in enumerate(future_cash_flows, 1)])

                # Calculate Terminal Value
                terminal_value = (future_cash_flows[-1] * (1 + terminal_growth_rate)) / (discount_rate - terminal_growth_rate)
                pv_terminal_value = terminal_value / ((1 + discount_rate) ** projection_years)

                # Calculate Total Enterprise Value
                total_pv = pv_future_cash_flows + pv_terminal_value

                # Note: A full DCF would add cash and subtract debt here to get Equity Value.
                # For this simple quick estimator, we use the PV directly or try to adjust if we have balance sheet data.
                # Since we didn't fetch Balance Sheet in this basic setup, we'll use Total PV as Equity Value proxy.
                intrinsic_value_per_share = total_pv / shares_out_input if shares_out_input > 0 else 0

                current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))

                st.markdown("### Valuation Results")
                res_col1, res_col2, res_col3 = st.columns(3)

                with res_col1:
                    st.metric("Estimated Intrinsic Value", f"${intrinsic_value_per_share:.2f}")
                with res_col2:
                    st.metric("Current Stock Price", f"${current_price:.2f}" if current_price else "N/A")
                with res_col3:
                    if current_price and current_price > 0:
                        margin = (intrinsic_value_per_share - current_price) / current_price
                        if intrinsic_value_per_share > current_price:
                            st.success(f"Undervalued by {margin*100:.1f}%")
                        else:
                            st.error(f"Overvalued by {abs(margin)*100:.1f}%")
                    else:
                        st.write("N/A")

            except ZeroDivisionError:
                st.error("Error in calculation: Discount rate must be strictly greater than Terminal Growth Rate.")
            except Exception as e:
                st.error(f"Error calculating DCF: {e}")

with tab_overview:
    st.header("Company Overview")

    if ticker_symbol:
        info = fetch_company_info(ticker_symbol)

        if info:
            st.subheader("Company Profile")
            st.write(info.get('longBusinessSummary', 'No description available.'))

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Sector:** {info.get('sector', 'N/A')}")
                st.markdown(f"**Industry:** {info.get('industry', 'N/A')}")
            with col2:
                st.markdown(f"**Country:** {info.get('country', 'N/A')}")
                st.markdown(f"**Full-Time Employees:** {info.get('fullTimeEmployees', 'N/A')}")
            with col3:
                website = info.get('website', 'N/A')
                st.markdown(f"**Website:** [{website}]({website})" if website != 'N/A' else "**Website:** N/A")

            st.divider()

            st.subheader("Recent News")
            news = fetch_news(ticker_symbol)
            if news:
                for article in news[:5]:
                    title = article.get('title', 'No Title')
                    link = article.get('link', '#')
                    publisher = article.get('publisher', 'Unknown')
                    st.markdown(f"[{title}]({link}) - *{publisher}*")
            else:
                st.write("No recent news available.")
        else:
            st.warning("No company information available for this ticker.")
