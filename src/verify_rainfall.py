from pathlib import Path
import rasterio

rainfall_dir = Path(__file__).resolve().parent.parent / "data" / "raw" / "rainfall"
files = sorted(rainfall_dir.glob("*.tif"))

print(f"Found {len(files)} .tif files")

if files:
    with rasterio.open(files[0]) as src:
        print("Sample file:", files[0].name)
        print("Shape:", src.shape)
        print("CRS:", src.crs)