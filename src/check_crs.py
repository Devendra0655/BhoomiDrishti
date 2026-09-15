from pathlib import Path
import rasterio
import geopandas as gpd

BASE_DIR = Path(__file__).resolve().parent.parent

v = gpd.read_file(BASE_DIR / 'data/shapefiles/vidarbha_districts_std.shp')
print('Shapefile CRS:', v.crs)
print('Shapefile bounds:', v.total_bounds)

hdf_path = BASE_DIR / 'data/raw/modis_ndvi/MOD13Q1.A2022353.h25v06.061.2023006045533.hdf'
with rasterio.open(f'HDF4_EOS:EOS_GRID:"{hdf_path}":MODIS_Grid_16DAY_250m_500m_VI:250m 16 days NDVI') as src:
    print('Raster CRS:', src.crs)
    print('Raster bounds:', src.bounds)