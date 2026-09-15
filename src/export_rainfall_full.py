"""
Export monthly CHIRPS rainfall totals for Vidarbha, 2010-2024,
as background Earth Engine tasks (runs on Google's servers).
"""

import ee
import geopandas as gpd
from pathlib import Path
import json

ee.Initialize(project='bhoomidrishti')

# Load Vidarbha boundary (same as before)
current = Path(__file__).resolve()
project_root = current.parent.parent
shapefile_path = project_root / "data" / "shapefiles" / "vidarbha_districts.shp"

vidarbha_gdf = gpd.read_file(shapefile_path)
geojson_dict = json.loads(vidarbha_gdf.to_json())
vidarbha_fc = ee.FeatureCollection(geojson_dict)
vidarbha_geometry = vidarbha_fc.geometry()

# CHIRPS full range
chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
    .filterDate('2010-01-01', '2024-12-31')

years = list(range(2010, 2025))  # 2010 to 2024 inclusive
months = list(range(1, 13))

task_count = 0

for year in years:
    for month in months:
        start = ee.Date.fromYMD(year, month, 1)
        end = start.advance(1, 'month')

        monthly_image = chirps.filterDate(start, end).sum() \
            .clip(vidarbha_geometry) \
            .set('year', year) \
            .set('month', month)

        filename = f"CHIRPS_Vidarbha_{year}_{month:02d}"

        task = ee.batch.Export.image.toDrive(
            image=monthly_image,
            description=filename,
            folder='BhoomiDrishti_Rainfall',   # will appear as this folder in your Google Drive
            fileNamePrefix=filename,
            region=vidarbha_geometry,
            scale=5000,
            maxPixels=1e9
        )
        task.start()
        task_count += 1
        print(f"Queued: {filename}")

print(f"\nAll {task_count} export tasks queued successfully!")
print("Check progress at: https://code.earthengine.google.com/tasks")
print("Files will appear in a Google Drive folder called 'BhoomiDrishti_Rainfall'")
print("This typically takes anywhere from 15 minutes to a couple hours depending on Earth Engine's queue.")