from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

BASE_DIR = Path(__file__).resolve().parent.parent

rainfall = pd.read_csv(BASE_DIR / "data/processed/vidarbha_rainfall_monthly.csv")
rainfall['date'] = pd.to_datetime(rainfall[['year', 'month']].assign(day=1))
rainfall = rainfall.sort_values(['DISTRICT_STD', 'date'])

rainfall['rain_3mo'] = (
    rainfall.groupby('DISTRICT_STD')['rainfall_mm']
    .transform(lambda s: s.rolling(3, min_periods=3).sum())
)

results = []

for district, dgroup in rainfall.groupby('DISTRICT_STD'):
    for month, mgroup in dgroup.groupby('month'):
        values = mgroup['rain_3mo'].dropna()
        if len(values) < 5:
            continue

        zero_mask = values == 0
        q = zero_mask.mean()
        nonzero = values[~zero_mask]

        if len(nonzero) >= 3:
            shape, loc, scale = stats.gamma.fit(nonzero, floc=0)
            cdf = np.where(
                zero_mask,
                q,
                q + (1 - q) * stats.gamma.cdf(values, shape, loc=loc, scale=scale),
            )
        else:
            cdf = stats.rankdata(values) / (len(values) + 1)

        cdf = np.clip(cdf, 1e-6, 1 - 1e-6)
        spi = stats.norm.ppf(cdf)

        for idx, val in zip(mgroup.index, spi):
            results.append({
                'DISTRICT_STD': district,
                'year': rainfall.loc[idx, 'year'],
                'month': month,
                'SPI3': val,
            })

spi_df = pd.DataFrame(results).sort_values(['DISTRICT_STD', 'year', 'month'])
spi_df = spi_df[spi_df['year'].between(2013, 2022)]

out_path = BASE_DIR / "data/processed/vidarbha_spi3.csv"
spi_df.to_csv(out_path, index=False)

print(f"Saved {len(spi_df)} rows to {out_path}")
print(spi_df.head(12))

print("\nSanity check — drought years (2015, 2018, 2019), mean SPI3 by district:")
print(spi_df[spi_df['year'].isin([2015, 2018, 2019])]
      .groupby(['DISTRICT_STD', 'year'])['SPI3'].mean().unstack())