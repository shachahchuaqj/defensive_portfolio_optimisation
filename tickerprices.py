import pandas as pd
import yfinance as yf
 
tickers = ["SPY", "TLT", "GLD", "FXF", "FXY"]
 
start = "2009-12-31"
end = None  # up to the latest available data
output = "prices.csv"

 
def download_prices(tickers, start, end) -> pd.DataFrame:
    data = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
    )
 
    if data.empty:
        raise RuntimeError("No data returned.")
 
    prices = data["Close"][tickers]
    prices.index = pd.to_datetime(prices.index).tz_localize(None)
    prices.index.name = "Date"
    return prices
 

prices = download_prices(tickers, start, end)
prices = prices.dropna(how="any")


def main():
    print(f"\nRows: {len(prices)}")
    print(f"Date range: {prices.index.min().date()} to {prices.index.max().date()}")

    # Save prices data to CSV file.
    prices.to_csv(output)
    print(f"\nSaved to {output}")
 
 
if __name__ == "__main__":
    main()