"""
STEP-BY-STEP: Test CHIRPS monthly rainfall aggregation
and district-clipping logic, using just 2015 as a trial run.
"""

import ee
import geopandas as gpd
from pathlib import Path
import json

# STEP 1: Connect to Earth Engine
ee.Initialize(project='bhoomidrishti')

# STEP 2: Load our Vidarbha districts shapefile and convert it
# into a format Earth Engine understands (an "ee.FeatureCollection")
current = Path(__file__).resolve()
project_root = current.parent.parent
shapefile_path = project_root / "data" / "shapefiles" / "vidarbha_districts.shp"

vidarbha_gdf = gpd.read_file(shapefile_path)

# Earth Engine needs coordinates in a specific JSON format (GeoJSON),
# so we convert our shapefile into that first
geojson_dict = json.loads(vidarbha_gdf.to_json())
vidarbha_fc = ee.FeatureCollection(geojson_dict)

print("Vidarbha boundary loaded into Earth Engine. District count:",
      vidarbha_gdf.shape[0])

# STEP 3: Load the CHIRPS daily rainfall dataset, filtered to 2015 only
chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
    .filterDate('2015-01-01', '2015-12-31')

# STEP 4: Build 12 monthly totals by summing daily rainfall within each month
months = ee.List.sequence(1, 12)

def monthly_sum(month):
    month = ee.Number(month)
    start = ee.Date.fromYMD(2015, month, 1)
    end = start.advance(1, 'month')
    monthly_image = chirps.filterDate(start, end).sum()
    return monthly_image.set('month', month).set('year', 2015)

monthly_collection = ee.ImageCollection.fromImages(months.map(monthly_sum))

# STEP 5: For each month, clip to Vidarbha and get the average rainfall
# across all 11 districts combined (a simple region-mean check)
def get_monthly_mean(image):
    stats = image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=vidarbha_fc.geometry(),
        scale=5000,
        maxPixels=1e9
    )
    return {
        'month': image.get('month').getInfo(),
        'mean_rainfall_mm': stats.get('precipitation').getInfo()
    }

print("\nFetching monthly rainfall for Vidarbha, 2015 (this may take ~30-60 seconds)...")
monthly_images = monthly_collection.toList(12)

results = []
for i in range(12):
    img = ee.Image(monthly_images.get(i))
    result = get_monthly_mean(img)
    results.append(result)
    print(f"Month {result['month']:2d}: {result['mean_rainfall_mm']:.2f} mm")

print("\nTest complete! If these numbers look like realistic monthly rainfall")
print("(roughly 0-50mm in dry months, 100-300+mm in monsoon months Jun-Sep),")
print("the logic is confirmed working.")