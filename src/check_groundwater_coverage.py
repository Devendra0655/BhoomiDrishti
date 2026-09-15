from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

gw = pd.read_csv(BASE_DIR / "data/raw/cgwb_groundwater/vidarbha_groundwater_std.csv")

print("Date range:", gw['date'].min(), "to", gw['date'].max())
print()

stations_per_district = gw.groupby('DISTRICT_STD')['station_name'].nunique()
print("Stations per district:")
print(stations_per_district)
print()

readings_per_station = gw.groupby(['DISTRICT_STD', 'station_name']).size()
print("Readings per station (min/max/mean within each district):")
print(readings_per_station.groupby('DISTRICT_STD').agg(['min', 'max', 'mean', 'count']))
print()

date_span_per_station = gw.groupby(['DISTRICT_STD', 'station_name'])['date'].agg(['min', 'max'])
print("Sample of date coverage per station (first 15 rows):")
print(date_span_per_station.head(15))