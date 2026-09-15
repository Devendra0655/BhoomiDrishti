"""
STEP-BY-STEP: Check that our India map file works,
and cut out only the 11 Vidarbha districts.
"""

import geopandas as gpd
from pathlib import Path

# STEP 1: Find the project root automatically (folder that contains 'data')
current = Path(__file__).resolve()
project_root = current.parent.parent  # src/check_shapefiles.py -> BhoomiDrishti/

shapefile_dir = project_root / "data" / "shapefiles"

# STEP 2: Find any .shp file with "adm2" in the name (case-insensitive)
matches = list(shapefile_dir.glob("*dm2*.shp")) + list(shapefile_dir.glob("*ADM2*.shp"))

if not matches:
    print("Could not find an adm2 shapefile. Here's what IS in that folder:")
    for f in shapefile_dir.iterdir():
        print(" -", f.name)
    raise SystemExit("Fix the folder/filename based on the list above, then rerun.")

shapefile_path = matches[0]
print("Using shapefile:", shapefile_path)

india_map = gpd.read_file(shapefile_path)

print("Total districts in India map:", len(india_map))
print("Column names:", india_map.columns.tolist())
print(india_map.head())

# STEP 3: Keep only Vidarbha's 11 districts
vidarbha_districts = [
    'Amravati', 'Yavatmal', 'Wardha', 'Nagpur', 'Akola',
    'Buldana', 'Washim', 'Bhandara', 'Gondiya', 'Chandrapur', 'Garhchiroli'
]

vidarbha_map = india_map[india_map['NAME_2'].isin(vidarbha_districts)]

print("Vidarbha districts found:", len(vidarbha_map))
print(vidarbha_map['NAME_2'].tolist())

# STEP 4: Save this smaller map for future use
output_path = project_root / "data" / "shapefiles" / "vidarbha_districts.shp"
vidarbha_map.to_file(output_path)
print("Saved! Check data/shapefiles folder for vidarbha_districts.shp")

