import streamlit as st
import yfinance as yf
import plotly.express as px
import pandas as pd

# App Title
st.title("Personal Stock Analysis Dashboard")

# User Inputs
ticker_symbol = st.text_input("Enter Stock Ticker (e.g., AAPL, GOOGL):", "AAPL")

time_ranges = {
    "1M": "1mo",
    "6M": "6mo",
    "1Y": "1y",
    "5Y": "5y"
}
selected_range = st.selectbox("Select Time Range:", list(time_ranges.keys()), index=2) # Default to "1Y"

if ticker_symbol:
    # Fetch Data
    ticker = yf.Ticker(ticker_symbol)
    period = time_ranges[selected_range]

    # Fetch historical data
    try:
        df = ticker.history(period=period)

        if not df.empty:
            # We have Open/High/Low/Close/Volume in the dataframe
            # For the basic chart, we plot "Close" price

            # Reset index to have Date as a column for plotly
            df = df.reset_index()

            # Create interactive Plotly chart
            fig = px.line(df, x="Date", y="Close", title=f"{ticker_symbol} Close Price ({selected_range})")
            fig.update_layout(xaxis_title="Date", yaxis_title="Price")

            # Display chart
            st.plotly_chart(fig, use_container_width=True)

            # Optionally, display raw data overview
            with st.expander("Show Raw Data (Open/High/Low/Close/Volume)"):
                st.dataframe(df[["Date", "Open", "High", "Low", "Close", "Volume"]])
        else:
            st.warning(f"No data found for ticker '{ticker_symbol}'. Please check the symbol and try again.")
    except Exception as e:
        st.error(f"Error fetching data: {e}")
