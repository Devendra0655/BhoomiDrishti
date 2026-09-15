import re
from pathlib import Path

import rasterio
import geopandas as gpd
import pandas as pd
from rasterstats import zonal_stats

BASE_DIR = Path(__file__).resolve().parent.parent

vidarbha = gpd.read_file(BASE_DIR / "data/shapefiles/vidarbha_districts_std.shp")
vidarbha = vidarbha.rename(columns={'DISTRICT_S': 'DISTRICT_STD'})

rainfall_folder = BASE_DIR / "data/raw/rainfall"
tif_files = sorted(rainfall_folder.glob("*.tif"))
print(f"Found {len(tif_files)} rainfall files")

results = []

for tif_file in tif_files:
    match = re.search(r'(\d{4})_(\d{2})', tif_file.name)
    if not match:
        print(f"Skipping {tif_file.name} - couldn't parse date")
        continue
    year, month = match.groups()

    with rasterio.open(tif_file) as src:
        rainfall_array = src.read(1)
        stats = zonal_stats(vidarbha, rainfall_array, affine=src.transform, stats=['mean'], nodata=src.nodata)

    for i, row in vidarbha.iterrows():
        value = stats[i]['mean']
        if value is not None:
            results.append({
                'DISTRICT_STD': row['DISTRICT_STD'],
                'year': int(year),
                'month': int(month),
                'rainfall_mm': value,
            })

rainfall_df = pd.DataFrame(results)
rainfall_df.to_csv(BASE_DIR / "data/processed/vidarbha_rainfall_monthly.csv", index=False)

print(f"Saved {len(rainfall_df)} rows")
print(rainfall_df.head())