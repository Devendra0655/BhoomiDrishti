from pathlib import Path
import geopandas as gpd
import pandas as pd
from district_mapping import standardize_district_name

BASE_DIR = Path(__file__).resolve().parent.parent

vidarbha = gpd.read_file(BASE_DIR / "data/shapefiles/vidarbha_districts.shp")
vidarbha['DISTRICT_STD'] = vidarbha['NAME_2'].apply(standardize_district_name)
vidarbha.to_file(BASE_DIR / "data/shapefiles/vidarbha_districts_std.shp")

gw = pd.read_csv(BASE_DIR / "data/raw/cgwb_groundwater/vidarbha_groundwater.csv")
gw['DISTRICT_STD'] = gw['district_name'].apply(standardize_district_name)
gw.to_csv(BASE_DIR / "data/raw/cgwb_groundwater/vidarbha_groundwater_std.csv", index=False)

print("Shapefile districts:", sorted(vidarbha['DISTRICT_STD'].unique()))
print("Groundwater districts:", sorted(gw['DISTRICT_STD'].unique()))