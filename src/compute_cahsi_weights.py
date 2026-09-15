from pathlib import Path
import pandas as pd
from scipy.stats import spearmanr

BASE_DIR = Path(__file__).resolve().parent.parent

ndvi = pd.read_csv(BASE_DIR / "data/processed/vidarbha_ndvi_anomaly.csv")
gw = pd.read_csv(BASE_DIR / "data/processed/groundwater_anomaly_district.csv")
spi = pd.read_csv(BASE_DIR / "data/processed/vidarbha_spi3.csv")
labels = pd.read_csv(BASE_DIR / "data/processed/drought_labels.csv")

ndvi['date'] = pd.to_datetime(ndvi['date'])
ndvi_harvest = ndvi[ndvi['date'].dt.month.between(9, 12)]
ndvi_agg = ndvi_harvest.groupby(['DISTRICT_STD', 'year'])['ndvi_anomaly'].mean().reset_index()

gw_kharif = gw[gw['reporting_window'].isin(['Monsoon', 'Post-monsoon'])]
gw_agg = gw_kharif.groupby(['DISTRICT_STD', 'year'])['GW_anomaly_median'].mean().reset_index()

spi_kharif = spi[spi['month'].between(6, 12)]
spi_agg = spi_kharif.groupby(['DISTRICT_STD', 'year'])['SPI3'].mean().reset_index()

merged = labels.merge(ndvi_agg, on=['DISTRICT_STD', 'year'], how='left') \
               .merge(gw_agg, on=['DISTRICT_STD', 'year'], how='left') \
               .merge(spi_agg, on=['DISTRICT_STD', 'year'], how='left')

complete = merged.dropna(subset=['ndvi_anomaly', 'GW_anomaly_median', 'SPI3'])
print(f"Rows with all 3 components present: {len(complete)}")

corr_ndvi, p_ndvi = spearmanr(complete['ndvi_anomaly'], complete['drought_label'])
corr_gw, p_gw = spearmanr(complete['GW_anomaly_median'], complete['drought_label'])
corr_spi, p_spi = spearmanr(complete['SPI3'], complete['drought_label'])

print("\nRaw Spearman correlations (NDVI: Sept-Dec harvest window; GW/SPI: Jun-Dec Kharif window):")
print(f"  NDVI Anomaly vs drought_label: r={corr_ndvi:.4f}, p={p_ndvi:.4f}")
print(f"  GW Anomaly   vs drought_label: r={corr_gw:.4f}, p={p_gw:.4f}")
print(f"  SPI-3        vs drought_label: r={corr_spi:.4f}, p={p_spi:.4f}")

total = abs(corr_ndvi) + abs(corr_gw) + abs(corr_spi)
w1, w2, w3 = abs(corr_ndvi)/total, abs(corr_gw)/total, abs(corr_spi)/total

print(f"\nDerived weights:")
print(f"  w1 (NDVI): {w1:.4f}")
print(f"  w2 (GW):   {w2:.4f}")
print(f"  w3 (SPI):  {w3:.4f}")
print(f"  Sum check: {w1+w2+w3:.6f}")

pd.DataFrame([{
    'w1_ndvi': w1, 'w2_gw': w2, 'w3_spi': w3,
    'corr_ndvi_raw': corr_ndvi, 'corr_gw_raw': corr_gw, 'corr_spi_raw': corr_spi,
    'p_ndvi': p_ndvi, 'p_gw': p_gw, 'p_spi': p_spi,
    'n_district_years': len(complete),
    'ndvi_window_note': 'Sept-Dec harvest-outcome window (lagging indicator)',
    'gw_spi_window_note': 'Jun-Dec Kharif accumulation window (leading indicators)',
    'gw_sign_note': 'weak/noisy at this sample size, not a clean inversion (see Pre-Step 1 log)',
}]).to_csv(BASE_DIR / "data/processed/cahsi_weights.csv", index=False)

print("\nSaved to data/processed/cahsi_weights.csv")