from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, r2_score

BASE_DIR = Path(__file__).resolve().parent.parent

df = pd.read_csv(BASE_DIR / "data/processed/cahsi_period_level.csv")
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values(['DISTRICT_STD', 'date']).reset_index(drop=True)

for lag in (1, 2, 3):
    df[f'gw_anomaly_lag{lag}'] = df.groupby('DISTRICT_STD')['gw_anomaly'].shift(lag)
    df[f'spi3_lag{lag}'] = df.groupby('DISTRICT_STD')['spi3'].shift(lag)

print("GW lag1 vs lag2 identical (stale, no new reading arrived):")
print((df['gw_anomaly_lag1'] == df['gw_anomaly_lag2']).mean())
print("SPI lag1 vs lag2 identical:")
print((df['spi3_lag1'] == df['spi3_lag2']).mean())

for h in (1, 2):
    df[f'CAHSI_t+{h}'] = df.groupby('DISTRICT_STD')['CAHSI'].shift(-h)
    df[f'persistence_pred_t+{h}'] = df['CAHSI']

def split_of(date):
    if pd.Timestamp('2013-01-01') <= date <= pd.Timestamp('2018-12-31'): return 'train'
    if pd.Timestamp('2019-01-01') <= date <= pd.Timestamp('2020-12-31'): return 'val'
    if pd.Timestamp('2021-01-01') <= date <= pd.Timestamp('2022-12-31'): return 'test'
    return None

df['split'] = df['date'].apply(split_of)

print("\nCAHSI mean/std per split:")
print(df.groupby('split')['CAHSI'].agg(['mean', 'std', 'count']))

for h in (1, 2):
    for split in ('val', 'test'):
        subset = df[(df['split'] == split)].dropna(subset=[f'CAHSI_t+{h}', f'persistence_pred_t+{h}'])
        rmse = np.sqrt(mean_squared_error(subset[f'CAHSI_t+{h}'], subset[f'persistence_pred_t+{h}']))
        r2 = r2_score(subset[f'CAHSI_t+{h}'], subset[f'persistence_pred_t+{h}'])
        print(f"Persistence baseline t+{h}, {split}: RMSE={rmse:.4f}, R2={r2:.4f}, n={len(subset)}")