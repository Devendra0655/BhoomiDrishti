from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

gw = pd.read_csv(BASE_DIR / "data/raw/cgwb_groundwater/vidarbha_groundwater_std.csv")
gw['date'] = pd.to_datetime(gw['date'])


def assign_window(month):
    if month == 1:
        return 'Winter'
    if month in (3, 4, 5):
        return 'Pre-monsoon'
    if month == 8:
        return 'Monsoon'
    if month == 11:
        return 'Post-monsoon'
    return None


gw['reporting_window'] = gw['date'].dt.month.apply(assign_window)
gw['year'] = gw['date'].dt.year

unmatched = gw['reporting_window'].isna().sum()
print(f"Readings outside the 4 reporting windows: {unmatched}/{len(gw)}")
gw = gw.dropna(subset=['reporting_window'])

station_stats = gw.groupby(['DISTRICT_STD', 'station_name']).agg(
    n_readings=('date', 'count'),
    first_date=('date', 'min'),
    last_date=('date', 'max'),
)
span_years = (gw['date'].max() - gw['date'].min()).days / 365.25
expected_readings = round(span_years * 4)
station_stats['years_span'] = (station_stats['last_date'] - station_stats['first_date']).dt.days / 365.25
station_stats['completeness'] = station_stats['n_readings'] / expected_readings

valid_stations = station_stats[
    (station_stats['completeness'] >= 0.5) & (station_stats['years_span'] >= 2)
].index

raw_counts = gw.groupby('DISTRICT_STD')['station_name'].nunique()
filtered_counts = pd.Series(
    [s for d, s in valid_stations], index=[d for d, s in valid_stations]
).groupby(level=0).count()

print("\nStation count before vs after filtering:")
print(pd.DataFrame({'raw': raw_counts, 'after_filter': filtered_counts}).fillna(0).astype(int))

gw = gw.set_index(['DISTRICT_STD', 'station_name'])
gw = gw.loc[gw.index.isin(valid_stations)].reset_index()

baselines = gw.groupby(['DISTRICT_STD', 'station_name', 'reporting_window'])['currentlevel'].mean()
baselines.name = 'station_window_baseline'

gw = gw.join(baselines, on=['DISTRICT_STD', 'station_name', 'reporting_window'])
gw['station_anomaly'] = (gw['currentlevel'] - gw['station_window_baseline']) / gw['station_window_baseline']

district_agg = gw.groupby(['DISTRICT_STD', 'year', 'reporting_window']).agg(
    GW_anomaly_median=('station_anomaly', 'median'),
    station_count=('station_anomaly', 'count'),
).reset_index()

out_path = BASE_DIR / "data/processed/groundwater_anomaly_district.csv"
out_path.parent.mkdir(parents=True, exist_ok=True)
district_agg.to_csv(out_path, index=False)
print(f"\nSaved {len(district_agg)} rows to {out_path}")

print("\nSanity check — drought years (2015, 2018, 2019):")
print(district_agg[district_agg['year'].isin([2015, 2018, 2019])]
      .sort_values(['year', 'DISTRICT_STD'])
      .to_string(index=False))