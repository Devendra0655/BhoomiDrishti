from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

ndvi = pd.read_csv(BASE_DIR / "data/raw/modis_ndvi/vidarbha_ndvi_timeseries.csv")
ndvi['date'] = pd.to_datetime(ndvi['date'])
ndvi['year'] = ndvi['date'].dt.year
ndvi['doy_period'] = ndvi['date'].dt.dayofyear

baseline = ndvi.groupby(['DISTRICT_STD', 'doy_period']).agg(
    ndvi_baseline=('ndvi', 'mean'),
    baseline_years=('ndvi', 'count'),
)

ndvi = ndvi.join(baseline, on=['DISTRICT_STD', 'doy_period'])
ndvi['ndvi_anomaly'] = (ndvi['ndvi'] - ndvi['ndvi_baseline']) / ndvi['ndvi_baseline']

out = ndvi[ndvi['year'].between(2013, 2022)][
    ['DISTRICT_STD', 'date', 'year', 'ndvi', 'ndvi_baseline', 'baseline_years', 'ndvi_anomaly']
].sort_values(['DISTRICT_STD', 'date'])

out_path = BASE_DIR / "data/processed/vidarbha_ndvi_anomaly.csv"
out.to_csv(out_path, index=False)

print(f"Saved {len(out)} rows to {out_path}")
print(out.head())

print("\nSanity check — mean NDVI anomaly, drought years (2015, 2018, 2019):")
print(out[out['year'].isin([2015, 2018, 2019])]
      .groupby(['DISTRICT_STD', 'year'])['ndvi_anomaly'].mean().unstack())

print("\nHow many periods per district have a thin baseline (< 8 contributing years)?")
print(out.groupby('DISTRICT_STD')['baseline_years'].apply(lambda s: (s < 8).sum()))