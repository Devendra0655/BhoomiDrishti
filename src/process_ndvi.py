import re
import multiprocessing as mp
from collections import defaultdict
from pathlib import Path

import rasterio
from rasterio.merge import merge
import geopandas as gpd
import pandas as pd
from rasterstats import zonal_stats

BASE_DIR = Path(__file__).resolve().parent.parent
SHAPEFILE = BASE_DIR / "data/shapefiles/vidarbha_districts_std.shp"
OUT_CSV = BASE_DIR / "data/raw/modis_ndvi/vidarbha_ndvi_timeseries.csv"


def process_one_date(date_str, tile_files, queue):
    vidarbha = gpd.read_file(SHAPEFILE).rename(columns={'DISTRICT_S': 'DISTRICT_STD'})
    srcs = []
    try:
        subdatasets = [
            f'HDF4_EOS:EOS_GRID:"{f}":MODIS_Grid_16DAY_250m_500m_VI:250m 16 days NDVI'
            for f in tile_files
        ]
        srcs = [rasterio.open(sd) for sd in subdatasets]
        mosaic, transform = merge(srcs)
        crs = srcs[0].crs
        vidarbha_proj = vidarbha.to_crs(crs)
        stats = zonal_stats(vidarbha_proj, mosaic[0], affine=transform, stats=['mean'], nodata=-3000)
        rows = []
        for i, row in vidarbha_proj.iterrows():
            val = stats[i]['mean']
            if val is not None:
                rows.append({'DISTRICT_STD': row['DISTRICT_STD'], 'date': date_str, 'ndvi': val / 10000.0})
        queue.put(('ok', rows))
    except Exception as e:
        queue.put(('error', str(e)))
    finally:
        for s in srcs:
            s.close()


def main():
    hdf_files = sorted((BASE_DIR / "data/raw/modis_ndvi").glob("*.hdf"))
    files_by_date = defaultdict(list)
    for hdf_file in hdf_files:
        match = re.search(r'A(\d{4})(\d{3})', hdf_file.name)
        if not match:
            continue
        year, doy = match.groups()
        date = pd.to_datetime(f"{year}-{doy}", format="%Y-%j")
        files_by_date[date].append(hdf_file)

    print(f"Found {len(hdf_files)} MODIS files across {len(files_by_date)} dates")

    all_results = []
    skipped = []

    for idx, (date, tile_files) in enumerate(sorted(files_by_date.items()), 1):
        date_str = date.strftime("%Y-%m-%d")
        print(f"[{idx}/{len(files_by_date)}] {date_str}...", end=" ", flush=True)

        queue = mp.Queue()
        p = mp.Process(target=process_one_date, args=(date_str, tile_files, queue))
        p.start()
        p.join(timeout=120)

        if p.is_alive():
            p.terminate()
            p.join()
            print("TIMEOUT - skipped")
            skipped.append((date_str, "timeout"))
        elif p.exitcode != 0:
            print(f"CRASHED (exit code {p.exitcode}) - skipped")
            skipped.append((date_str, f"crashed, exit code {p.exitcode}"))
        else:
            status, payload = queue.get()
            if status == 'ok':
                all_results.extend(payload)
                print("OK")
            else:
                print(f"SKIPPED - {payload}")
                skipped.append((date_str, payload))

        if idx % 20 == 0:
            pd.DataFrame(all_results).to_csv(OUT_CSV, index=False)
            print(f"    (progress saved: {len(all_results)} rows so far)")

    ndvi_df = pd.DataFrame(all_results)
    ndvi_df.to_csv(OUT_CSV, index=False)

    print(f"\nSaved {len(ndvi_df)} rows to {OUT_CSV}")
    print(ndvi_df.head())
    print(f"\nSkipped {len(skipped)} dates:")
    for d, reason in skipped:
        print(f"  {d}: {reason}")


if __name__ == "__main__":
    main()