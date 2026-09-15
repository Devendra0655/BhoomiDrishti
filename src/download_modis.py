"""
STEP-BY-STEP: Download MODIS NDVI data for Vidarbha region
Run this file directly in PyCharm using the green Run button.
"""
import earthaccess

# STEP 1: Login to NASA Earthdata
# This will ask for your username and password in the terminal below.
auth = earthaccess.login(strategy="interactive", persist=True)
print("Login successful:", auth.authenticated)

# STEP 2: Search for MODIS NDVI data over Vidarbha
VIDARBHA_BOUNDING_BOX = (76.0, 19.0, 80.5, 21.5)

results = earthaccess.search_data(
    short_name="MOD13Q1",
    bounding_box=VIDARBHA_BOUNDING_BOX,
    temporal=("2023-01-01", "2023-03-01"),
)

print(f"Found {len(results)} files matching Vidarbha region and date range")

# STEP 3: Download the files
downloaded_files = earthaccess.download(
    results,
    "data/raw/modis_ndvi/"
)

print("Downloaded files:")
for f in downloaded_files:
    print(" -", f)

print("\nDONE. Check the data/raw/modis_ndvi folder for .hdf files.")