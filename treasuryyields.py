import pandas as pd

# fetching 3-month Treasury Yield data from FRED (Federal Reserve Economic Data). 
series = "DGS3MO"
url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
start = "2009-12-31"
output = "rf.csv"
 
 
def download_rf(start=start) -> pd.DataFrame:
    raw = pd.read_csv(
        url,
        parse_dates=["observation_date"],
        index_col="observation_date",
    )
    raw.index.name = "Date"

    rf_percent = pd.to_numeric(raw[series], errors="coerce")
    rf = (rf_percent / 100.0).rename("rf_annual")       # decimalise the risk-free rate.
    rf = rf.loc[start:].ffill()
    return rf.to_frame()
  

rf = download_rf() # DataFrame containing data on the risk-free rate.

 
def main():
    rf = download_rf()

    print(f"Date range: {rf.index.min().date()} to {rf.index.max().date()}")
    print(f"Missing values after ffill: {int(rf['rf_annual'].isna().sum())}")
 
    rf.to_csv(output)
    print(f"\nSaved to {output}")
 
if __name__ == "__main__":
    main()
