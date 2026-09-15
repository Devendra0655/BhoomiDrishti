from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

W1, W2, W3 = 0.3114, 0.2237, 0.4649

ndvi = pd.read_csv(BASE_DIR / "data/processed/vidarbha_ndvi_anomaly.csv")
gw = pd.read_csv(BASE_DIR / "data/processed/groundwater_anomaly_district.csv")
spi = pd.read_csv(BASE_DIR / "data/processed/vidarbha_spi3.csv")

ndvi['date'] = pd.to_datetime(ndvi['date'])

WINDOW_ORDER = {'Winter': 1, 'Pre-monsoon': 3, 'Monsoon': 8, 'Post-monsoon': 11}
gw['window_month'] = gw['reporting_window'].map(WINDOW_ORDER)
gw['gw_date'] = pd.to_datetime(gw['year'].astype(str) + '-' + gw['window_month'].astype(str) + '-01')
gw = gw[['DISTRICT_STD', 'gw_date', 'GW_anomaly_median']].sort_values(['DISTRICT_STD', 'gw_date'])

spi['spi_date'] = pd.to_datetime(spi['year'].astype(str) + '-' + spi['month'].astype(str) + '-01')
spi = spi[['DISTRICT_STD', 'spi_date', 'SPI3']].sort_values(['DISTRICT_STD', 'spi_date'])

GW_STALE_LIMIT = pd.Timedelta(days=100)   # one CGWB quarterly cycle + buffer
SPI_STALE_LIMIT = pd.Timedelta(days=35)   # one month + buffer

rows = []
for district, dgroup in ndvi.sort_values(['DISTRICT_STD', 'date']).groupby('DISTRICT_STD'):
    gw_d = gw[gw['DISTRICT_STD'] == district]
    spi_d = spi[spi['DISTRICT_STD'] == district]

    for _, r in dgroup.iterrows():
        gw_prior = gw_d[gw_d['gw_date'] <= r['date']]
        spi_prior = spi_d[spi_d['spi_date'] <= r['date']]

        gw_val, gw_used = None, False
        if not gw_prior.empty:
            last = gw_prior.iloc[-1]
            if r['date'] - last['gw_date'] <= GW_STALE_LIMIT:
                gw_val, gw_used = last['GW_anomaly_median'], True

        spi_val, spi_used = None, False
        if not spi_prior.empty:
            last = spi_prior.iloc[-1]
            if r['date'] - last['spi_date'] <= SPI_STALE_LIMIT:
                spi_val, spi_used = last['SPI3'], True

        weights_available = {'ndvi': W1}
        components = {'ndvi': r['ndvi_anomaly']}
        if gw_used:
            weights_available['gw'] = W2
            components['gw'] = gw_val
        if spi_used:
            weights_available['spi'] = W3
            components['spi'] = spi_val

        weight_sum = sum(weights_available.values())
        cahsi = sum(components[k] * weights_available[k] / weight_sum for k in components)

        rows.append({
            'DISTRICT_STD': district,
            'date': r['date'],
            'year': r['year'],
            'ndvi_anomaly': r['ndvi_anomaly'],
            'gw_anomaly': gw_val,
            'spi3': spi_val,
            'gw_used': gw_used,
            'spi_used': spi_used,
            'CAHSI': cahsi,
        })

cahsi_df = pd.DataFrame(rows)
out_path = BASE_DIR / "data/processed/cahsi_period_level.csv"
cahsi_df.to_csv(out_path, index=False)

print(f"Saved {len(cahsi_df)} rows to {out_path}")
print(f"\nRows where GW was stale/missing (component substitution used): {(~cahsi_df['gw_used']).sum()}")
print(f"Rows where SPI was stale/missing (component substitution used): {(~cahsi_df['spi_used']).sum()}")

print("\nSanity check — mean CAHSI, drought years (2015, 2018, 2019) vs. others, per district:")
cahsi_df['is_drought_year'] = cahsi_df['year'].isin([2015, 2018, 2019])
print(cahsi_df.groupby(['DISTRICT_STD', 'is_drought_year'])['CAHSI'].mean().unstack())

print("\nYavatmal and Amravati — CAHSI by year (mean):")
print(cahsi_df[cahsi_df['DISTRICT_STD'].isin(['Yavatmal', 'Amravati'])]
      .groupby(['DISTRICT_STD', 'year'])['CAHSI'].mean().unstack())