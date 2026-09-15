from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

ndvi = pd.read_csv(BASE_DIR / "data/processed/vidarbha_ndvi_anomaly.csv")
gw = pd.read_csv(BASE_DIR / "data/processed/groundwater_anomaly_district.csv")
spi = pd.read_csv(BASE_DIR / "data/processed/vidarbha_spi3.csv")

ndvi['date'] = pd.to_datetime(ndvi['date'])
ndvi_2015_pm = ndvi[(ndvi['year'] == 2015) & (ndvi['date'].dt.month.isin([3, 4, 5]))]
ndvi_avail = ndvi_2015_pm.groupby('DISTRICT_STD')['ndvi_anomaly'].mean()

gw_2015_pm = gw[(gw['year'] == 2015) & (gw['reporting_window'] == 'Pre-monsoon')]
gw_avail = gw_2015_pm.set_index('DISTRICT_STD')['GW_anomaly_median']

spi_2015_pm = spi[(spi['year'] == 2015) & (spi['month'].isin([3, 4, 5]))]
spi_avail = spi_2015_pm.groupby('DISTRICT_STD')['SPI3'].mean()

districts = ['Akola', 'Amravati', 'Bhandara', 'Buldhana', 'Chandrapur',
             'Gadchiroli', 'Gondia', 'Nagpur', 'Wardha', 'Washim', 'Yavatmal']

coverage = pd.DataFrame({
    'NDVI_anomaly': ndvi_avail.reindex(districts),
    'GW_anomaly': gw_avail.reindex(districts),
    'SPI3': spi_avail.reindex(districts),
})

print("2015 Pre-monsoon (Mar-May) coverage across all 3 components:")
print(coverage)
print("\nMissing counts per component:")
print(coverage.isna().sum())