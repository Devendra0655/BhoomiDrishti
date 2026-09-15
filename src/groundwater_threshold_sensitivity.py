from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

gw = pd.read_csv(BASE_DIR / "data/raw/cgwb_groundwater/vidarbha_groundwater_std.csv")
gw['date'] = pd.to_datetime(gw['date'])

span_years = (gw['date'].max() - gw['date'].min()).days / 365.25
expected_readings = round(span_years * 4)
print(f"Date span: {span_years:.1f} years -> expected ~{expected_readings} quarterly readings per station")
print()

station_summary = gw.groupby(['DISTRICT_STD', 'station_name']).agg(
    n_readings=('date', 'count'),
    first_date=('date', 'min'),
    last_date=('date', 'max'),
)
station_summary['years_span'] = (station_summary['last_date'] - station_summary['first_date']).dt.days / 365.25
station_summary['completeness'] = station_summary['n_readings'] / expected_readings

thresholds = [0.4, 0.5, 0.6]

for pct in thresholds:
    print(f"--- Threshold: >= {int(pct*100)}% completeness AND >= 2 years span ---")
    passed = station_summary[
        (station_summary['completeness'] >= pct) &
        (station_summary['years_span'] >= 2)
    ]
    counts = passed.groupby('DISTRICT_STD').size()
    total_stations = station_summary.groupby('DISTRICT_STD').size()
    comparison = pd.DataFrame({'total_stations': total_stations, 'passing_stations': counts}).fillna(0).astype(int)
    comparison['pct_retained'] = (comparison['passing_stations'] / comparison['total_stations'] * 100).round(1)
    print(comparison)
    print()