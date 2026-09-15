from pathlib import Path
import earthaccess
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
out_dir = BASE_DIR / "data/raw/modis_ndvi"
out_dir.mkdir(parents=True, exist_ok=True)

auth = earthaccess.login()
print("Authenticated:", auth.authenticated)
if not auth.authenticated:
    print("STOP: not authenticated.")
    raise SystemExit

results = earthaccess.search_data(
    short_name="MOD13Q1",
    version="061",
    temporal=("2011-01-01", "2023-12-31"),
    bounding_box=(75.92, 18.67, 80.90, 21.78),
)
print(f"Found {len(results)} granules")

session = requests.Session()
session.trust_env = True

successful, skipped, failed = 0, 0, []

for i, granule in enumerate(results):
    hdf_links = [link for link in granule.data_links() if link.endswith(".hdf")]
    if not hdf_links:
        print(f"[{i+1}/{len(results)}] No .hdf link found, skipping")
        skipped += 1
        continue

    url = hdf_links[0]
    filename = url.split("/")[-1]
    filepath = out_dir / filename

    if filepath.exists():
        successful += 1
        continue

    try:
        print(f"[{i+1}/{len(results)}] Downloading: {filename}")
        response = session.get(url, stream=True, allow_redirects=True, timeout=60)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        successful += 1
        print(f"    Done ({filepath.stat().st_size / 1024:.1f} KB)")

    except requests.exceptions.Timeout:
        print("    TIMEOUT after 60s - skipping")
        if filepath.exists():
            filepath.unlink()
        failed.append(filename)
    except Exception as e:
        print(f"    ERROR: {e}")
        if filepath.exists():
            filepath.unlink()
        failed.append(filename)

print(f"\nSuccessful: {successful}/{len(results)}")
print(f"Skipped (no .hdf link): {skipped}")
print(f"Failed: {len(failed)}")
if failed:
    print("Failed files:", failed)
